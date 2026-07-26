FROM golang:1.21-alpine AS builder

WORKDIR /app

# Initialize a dummy module
RUN go mod init content-service

COPY main.go .

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -o server main.go

FROM alpine:latest
WORKDIR /app

# Copy the binary and templates
COPY --from=builder /app/server .
COPY templates/ ./templates/

# Expose port
EXPOSE 8000

# Run the binary
CMD ["./server"]
