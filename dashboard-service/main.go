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
	Timestamp       int64   `json:"timestamp"`
	RpsMedia        float64 `json:"rps_media"`
	RpsContent      float64 `json:"rps_content"`
	CpuMedia        float64 `json:"cpu_media"`
	CpuContent      float64 `json:"cpu_content"`
	RamMedia        float64 `json:"ram_media"`
	RamContent      float64 `json:"ram_content"`
	ReplicasMedia   float64 `json:"replicas_media"`
	ReplicasContent float64 `json:"replicas_content"`
	LatencyMedia    float64 `json:"latency_media"`
	LatencyContent  float64 `json:"latency_content"`
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
		"rps_media":        `sum(rate(haproxy_backend_http_requests_total{proxy="media_back"}[10s]))`,
		"rps_content":      `sum(rate(haproxy_backend_http_requests_total{proxy="content_back"}[10s]))`,
		"cpu_media":        `sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service="media-service"}[10s])) * 100`,
		"cpu_content":      `sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service="content-service"}[10s])) * 100`,
		"ram_media":        `sum(container_memory_working_set_bytes{container_label_com_docker_compose_service="media-service"}) / 1024 / 1024`,
		"ram_content":      `sum(container_memory_working_set_bytes{container_label_com_docker_compose_service="content-service"}) / 1024 / 1024`,
		"replicas_media":   `count(container_last_seen{container_label_com_docker_compose_service="media-service"} > time() - 15)`,
		"replicas_content": `count(container_last_seen{container_label_com_docker_compose_service="content-service"} > time() - 15)`,
		"latency_media":    `sum(haproxy_backend_response_time_average_seconds{proxy="media_back"}) * 1000`,
		"latency_content":  `sum(haproxy_backend_response_time_average_seconds{proxy="content_back"}) * 1000`,
	}

	var wg sync.WaitGroup
	var mu sync.Mutex

	for key, query := range queries {
		wg.Add(1)
		go func(k, q string) {
			defer wg.Done()
			val, err := queryPrometheus(promURL, q)
			if err != nil {
				log.Printf("Error querying Prometheus for key %s: %v", k, err)
				return
			}
			mu.Lock()
			switch k {
			case "rps_media":
				payload.RpsMedia = val
			case "rps_content":
				payload.RpsContent = val
			case "cpu_media":
				payload.CpuMedia = val
			case "cpu_content":
				payload.CpuContent = val
			case "ram_media":
				payload.RamMedia = val
			case "ram_content":
				payload.RamContent = val
			case "replicas_media":
				payload.ReplicasMedia = val
			case "replicas_content":
				payload.ReplicasContent = val
			case "latency_media":
				payload.LatencyMedia = val
			case "latency_content":
				payload.LatencyContent = val
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
