package main

import (
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"sync"
	"time"
)

//go:embed index.html
var frontendFS embed.FS

// Message represents the SSE payload
type MetricsPayload struct {
	Timestamp    int64   `json:"timestamp"`
	RpsAuth      float64 `json:"rps_auth"`
	RpsQuiz      float64 `json:"rps_quiz"`
	CpuAuth      float64 `json:"cpu_auth"`
	CpuQuiz      float64 `json:"cpu_quiz"`
	RamAuth      float64 `json:"ram_auth"`
	RamQuiz      float64 `json:"ram_quiz"`
	ReplicasAuth float64 `json:"replicas_auth"`
	ReplicasQuiz float64 `json:"replicas_quiz"`
}

// Client represents a connected SSE client
type Client chan string

// Broker manages active SSE client connections
type Broker struct {
	clients    map[Client]bool
	newClients chan Client
	defunct    chan Client
	messages   chan string
	mu         sync.RWMutex
}

func NewBroker() *Broker {
	return &Broker{
		clients:    make(map[Client]bool),
		newClients: make(chan Client),
		defunct:    make(chan Client),
		messages:   make(chan string),
	}
}

func (b *Broker) Start() {
	for {
		select {
		case c := <-b.newClients:
			b.mu.Lock()
			b.clients[c] = true
			b.mu.Unlock()
			log.Printf("New client connected. Total clients: %d", len(b.clients))

		case c := <-b.defunct:
			b.mu.Lock()
			delete(b.clients, c)
			close(c)
			b.mu.Unlock()
			log.Printf("Client disconnected. Total clients: %d", len(b.clients))

		case msg := <-b.messages:
			b.mu.RLock()
			for client := range b.clients {
				select {
				case client <- msg:
				default:
					// Slow consumer, skip
				}
			}
			b.mu.RUnlock()
		}
	}
}

func queryPrometheus(promURL, query string) (float64, error) {
	apiURL := fmt.Sprintf("%s/api/v1/query?query=%s", promURL, url.QueryEscape(query))
	ctx, cancel := context.WithTimeout(context.Background(), 800*time.Millisecond)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, "GET", apiURL, nil)
	if err != nil {
		return 0, err
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("status code %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return 0, err
	}

	var result struct {
		Status string `json:"status"`
		Data   struct {
			ResultType string `json:"resultType"`
			Result     []struct {
				Value []interface{} `json:"value"`
			} `json:"result"`
		} `json:"data"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return 0, err
	}

	if len(result.Data.Result) == 0 || len(result.Data.Result[0].Value) < 2 {
		return 0, nil // No data points yet
	}

	valStr, ok := result.Data.Result[0].Value[1].(string)
	if !ok {
		return 0, nil
	}

	var val float64
	_, err = fmt.Sscanf(valStr, "%f", &val)
	if err != nil {
		return 0, err
	}

	return val, nil
}

func collectMetrics(promURL string) MetricsPayload {
	var payload MetricsPayload
	payload.Timestamp = time.Now().Unix()

	queries := map[string]string{
		"rps_auth":      `sum(idelta(haproxy_backend_http_requests_total{proxy="auth_back"}[2s]))`,
		"rps_quiz":      `sum(idelta(haproxy_backend_http_requests_total{proxy="quiz_back"}[2s]))`,
		"cpu_auth":      `sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service="auth-service"}[5s])) * 100`,
		"cpu_quiz":      `sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service="quiz-service"}[5s])) * 100`,
		"ram_auth":      `sum(container_memory_working_set_bytes{container_label_com_docker_compose_service="auth-service"}) / 1024 / 1024`,
		"ram_quiz":      `sum(container_memory_working_set_bytes{container_label_com_docker_compose_service="quiz-service"}) / 1024 / 1024`,
		"replicas_auth": `count(container_last_seen{container_label_com_docker_compose_service="auth-service"})`,
		"replicas_quiz": `count(container_last_seen{container_label_com_docker_compose_service="quiz-service"})`,
	}

	var wg sync.WaitGroup
	var mu sync.Mutex

	for key, query := range queries {
		wg.Add(1)
		go func(k, q string) {
			defer wg.Done()
			val, err := queryPrometheus(promURL, q)
			if err != nil {
				return
			}
			mu.Lock()
			switch k {
			case "rps_auth":
				payload.RpsAuth = val
			case "rps_quiz":
				payload.RpsQuiz = val
			case "cpu_auth":
				payload.CpuAuth = val
			case "cpu_quiz":
				payload.CpuQuiz = val
			case "ram_auth":
				payload.RamAuth = val
			case "ram_quiz":
				payload.RamQuiz = val
			case "replicas_auth":
				payload.ReplicasAuth = val
			case "replicas_quiz":
				payload.ReplicasQuiz = val
			}
			mu.Unlock()
		}(key, query)
	}

	wg.Wait()
	return payload
}

func main() {
	promURL := os.Getenv("PROMETHEUS_URL")
	if promURL == "" {
		promURL = "http://prometheus:9090"
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "3002"
	}

	broker := NewBroker()
	go broker.Start()

	// Metric Collection Loop (every 1 second)
	go func() {
		ticker := time.NewTicker(1 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			payload := collectMetrics(promURL)
			data, err := json.Marshal(payload)
			if err == nil {
				broker.messages <- string(data)
			}
		}
	}()

	// HTTP Routing
	mux := http.NewServeMux()

	// Serve Embedded index.html
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		data, err := frontendFS.ReadFile("index.html")
		if err != nil {
			http.Error(w, "Not Found", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write(data)
	})

	// SSE Events Endpoint
	mux.HandleFunc("/events", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")
		w.Header().Set("Access-Control-Allow-Origin", "*")

		flusher, ok := w.(http.Flusher)
		if !ok {
			http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
			return
		}

		clientChan := make(Client)
		broker.newClients <- clientChan

		defer func() {
			broker.defunct <- clientChan
		}()

		fmt.Fprintf(w, "event: connected\ndata: {}\n\n")
		flusher.Flush()

		for {
			select {
			case msg, open := <-clientChan:
				if !open {
					return
				}
				fmt.Fprintf(w, "data: %s\n\n", msg)
				flusher.Flush()
			case <-r.Context().Done():
				return
			}
		}
	})

	serverURL := fmt.Sprintf(":%s", port)
	log.Printf("Dashboard Service starting on %s...", serverURL)
	log.Printf("Connecting to Prometheus at %s...", promURL)
	if err := http.ListenAndServe(serverURL, mux); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}
