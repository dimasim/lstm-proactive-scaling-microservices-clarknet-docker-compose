# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy files
COPY main.go index.html ./

# Initialize module and build minimal binary
RUN go mod init dashboard-service && CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o dashboard-service .

# Run stage
FROM alpine:latest

WORKDIR /app

COPY --from=builder /app/dashboard-service .

# Default environment variables
ENV PORT=3002
ENV PROMETHEUS_URL=http://prometheus:9090

EXPOSE 3002

CMD ["./dashboard-service"]
