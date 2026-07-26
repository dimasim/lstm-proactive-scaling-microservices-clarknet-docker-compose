package main

import (
	"crypto/md5"
	"encoding/hex"
	"fmt"
	"html/template"
	"net/http"
	"os"
	"sort"
	"strconv"
)

type User struct {
	Username string
	IP       string
	Node     string
	Baud     string
	Duration int
}

var mockUsersSorted []User
var cpuLoadIterations int

func init() {
	var mockUsers []User
	for i := 1; i <= 150; i++ {
		username := fmt.Sprintf("clark_usr%03d", i)
		ip := fmt.Sprintf("198.137.240.%d", i)
		node := fmt.Sprintf("MD-BALT-NODE-%d", ((i-1)%5)+1)
		baud := "14400"
		if i%2 == 0 {
			baud = "28800"
		}
		duration := (i * 7) % 180

		mockUsers = append(mockUsers, User{
			Username: username,
			IP:       ip,
			Node:     node,
			Baud:     baud,
			Duration: duration,
		})
	}

	sort.Slice(mockUsers, func(i, j int) bool {
		return mockUsers[i].Duration > mockUsers[j].Duration
	})
	mockUsersSorted = mockUsers

	envIters := os.Getenv("CPU_LOAD_ITERATIONS")
	if envIters != "" {
		if val, err := strconv.Atoi(envIters); err == nil {
			cpuLoadIterations = val
		}
	}
	if cpuLoadIterations == 0 {
		cpuLoadIterations = 10000 // Default value
	}
}

func applyArtificialCPULoad() {
	for i := 0; i < cpuLoadIterations; i++ {
		hash := md5.Sum([]byte("ClarkNet-Proactive-Scaling-Simulation"))
		_ = hash
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status": "healthy"}`))
}

func contentHandler(w http.ResponseWriter, r *http.Request) {
	applyArtificialCPULoad()

	// Simulate lightweight billing check
	hash := md5.Sum([]byte("billing_check"))
	_ = hex.EncodeToString(hash[:])

	// Simulate RAM usage (500 KB per request)
	tempBuffer := make([]byte, 500*1024)
	tempBuffer[0] = 1
	tempBuffer[len(tempBuffer)-1] = 1
	_ = tempBuffer

	// Parse and execute template
	tmpl, err := template.ParseFiles("templates/clarknet.html")
	if err != nil {
		http.Error(w, "Template error: "+err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/html")
	err = tmpl.Execute(w, map[string]interface{}{
		"users": mockUsersSorted,
	})
	if err != nil {
		fmt.Println("Error executing template:", err)
	}
}

func main() {
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/content", contentHandler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	fmt.Printf("Content Service started on port %s with CPU load iterations: %d\n", port, cpuLoadIterations)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		fmt.Println("Error starting server:", err)
	}
}
