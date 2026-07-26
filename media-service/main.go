package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math/rand"
	"net/http"
	"os"
	"strconv"
)

var images = []string{
	"20250928_051902.jpg",
	"20250928_075112.jpg",
	"20250928_080239.jpg",
}

var cachedImages map[string][]byte
var cpuLoadIterations int

func init() {
	cachedImages = make(map[string][]byte)
	dummyHeader := []byte("FFD8FFE000104A464946")
	dummyBody := make([]byte, 1000)
	for i := range dummyBody {
		dummyBody[i] = '0'
	}
	for _, imgName := range images {
		cachedImages[imgName] = append(dummyHeader, dummyBody...)
	}

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
	// Loop to simulate CPU computation.
	// Adjust CPU_LOAD_ITERATIONS environment variable to perfectly hit the SLA limit at 14 RPS.
	for i := 0; i < cpuLoadIterations; i++ {
		hash := sha256.Sum256([]byte("ClarkNet-Proactive-Scaling-Simulation"))
		_ = hash
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
}

func mediaHandler(w http.ResponseWriter, r *http.Request) {
	applyArtificialCPULoad()

	selectedImage := images[rand.Intn(len(images))]
	imgBytes := cachedImages[selectedImage]

	// Simulate RAM usage (500 KB per request)
	tempBuffer := make([]byte, 500*1024)
	tempBuffer[0] = 1
	tempBuffer[len(tempBuffer)-1] = 1
	_ = tempBuffer

	hash := sha256.Sum256([]byte(selectedImage))
	hashHex := hex.EncodeToString(hash[:])

	w.Header().Set("Content-Type", "image/jpeg")
	w.Header().Set("X-Image-Hash", hashHex)
	w.Write(imgBytes)
}

func main() {
	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/media", mediaHandler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	fmt.Printf("Media Service started on port %s with CPU load iterations: %d\n", port, cpuLoadIterations)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		fmt.Println("Error starting server:", err)
	}
}
