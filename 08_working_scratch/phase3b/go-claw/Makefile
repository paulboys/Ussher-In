.PHONY: build test clean fmt vet

BIN_DIR := bin

build:
	@mkdir -p $(BIN_DIR)
	go build -o $(BIN_DIR)/claw-verify ./cmd/claw-verify
	go build -o $(BIN_DIR)/claw-server ./cmd/claw-server

test:
	go test ./...

fmt:
	go fmt ./...

vet:
	go vet ./...

clean:
	rm -rf $(BIN_DIR)
