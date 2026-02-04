#!/bin/bash
# =============================================================================
# Ollama Management Script
# =============================================================================

set -e

# Colors
BLUE='\033[34m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
RESET='\033[0m'

# Default models
CHAT_MODEL="${OLLAMA_MODEL:-qwen2.5:32b}"
EMBEDDING_MODEL="${OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}"

# Functions
print_header() {
    echo -e "${BLUE}=============================================${RESET}"
    echo -e "${BLUE}  Ollama Management - Agentic AI Platform${RESET}"
    echo -e "${BLUE}=============================================${RESET}"
}

check_ollama() {
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}Error: Ollama is not installed${RESET}"
        echo "Install from: https://ollama.ai"
        exit 1
    fi
}

is_running() {
    curl -s http://localhost:11434/api/tags > /dev/null 2>&1
}

cmd_status() {
    echo -e "${BLUE}Checking Ollama status...${RESET}"
    
    if is_running; then
        echo -e "${GREEN}✓ Ollama is running${RESET}"
        echo ""
        echo "Installed models:"
        ollama list
    else
        echo -e "${YELLOW}✗ Ollama is not running${RESET}"
        echo "Run: ollama serve"
    fi
}

cmd_start() {
    echo -e "${BLUE}Starting Ollama...${RESET}"
    
    if is_running; then
        echo -e "${YELLOW}Ollama is already running${RESET}"
        return
    fi
    
    # Start in background
    nohup ollama serve > /tmp/ollama.log 2>&1 &
    
    # Wait for startup
    echo -n "Waiting for Ollama to start"
    for i in {1..30}; do
        if is_running; then
            echo ""
            echo -e "${GREEN}✓ Ollama started${RESET}"
            return
        fi
        echo -n "."
        sleep 1
    done
    
    echo ""
    echo -e "${RED}Failed to start Ollama. Check /tmp/ollama.log${RESET}"
    exit 1
}

cmd_stop() {
    echo -e "${BLUE}Stopping Ollama...${RESET}"
    
    # Find and kill ollama process
    pkill -f "ollama serve" 2>/dev/null || true
    
    echo -e "${GREEN}✓ Ollama stopped${RESET}"
}

cmd_pull() {
    echo -e "${BLUE}Pulling required models...${RESET}"
    echo ""
    
    if ! is_running; then
        echo -e "${YELLOW}Starting Ollama first...${RESET}"
        cmd_start
    fi
    
    echo -e "${BLUE}Pulling chat model: ${CHAT_MODEL}${RESET}"
    ollama pull "$CHAT_MODEL"
    echo ""
    
    echo -e "${BLUE}Pulling embedding model: ${EMBEDDING_MODEL}${RESET}"
    ollama pull "$EMBEDDING_MODEL"
    echo ""
    
    echo -e "${GREEN}✓ All models pulled${RESET}"
}

cmd_test() {
    echo -e "${BLUE}Testing Ollama connection...${RESET}"
    
    if ! is_running; then
        echo -e "${RED}Ollama is not running${RESET}"
        exit 1
    fi
    
    echo ""
    echo -e "${BLUE}Testing chat model (${CHAT_MODEL})...${RESET}"
    response=$(ollama run "$CHAT_MODEL" "Say 'Hello from Ollama' and nothing else" 2>/dev/null || echo "FAILED")
    
    if [[ "$response" == *"Hello"* ]]; then
        echo -e "${GREEN}✓ Chat model working${RESET}"
        echo "Response: $response"
    else
        echo -e "${RED}✗ Chat model failed${RESET}"
        echo "Make sure to run: make ollama-pull"
    fi
    
    echo ""
    echo -e "${BLUE}Testing embedding model (${EMBEDDING_MODEL})...${RESET}"
    
    # Test embeddings API
    embed_response=$(curl -s http://localhost:11434/api/embeddings \
        -d "{\"model\": \"$EMBEDDING_MODEL\", \"prompt\": \"test\"}" 2>/dev/null || echo "FAILED")
    
    if [[ "$embed_response" == *"embedding"* ]]; then
        echo -e "${GREEN}✓ Embedding model working${RESET}"
    else
        echo -e "${RED}✗ Embedding model failed${RESET}"
        echo "Make sure to run: make ollama-pull"
    fi
}

cmd_models() {
    echo -e "${BLUE}Available models:${RESET}"
    echo ""
    
    if ! is_running; then
        echo -e "${YELLOW}Ollama is not running. Starting...${RESET}"
        cmd_start
    fi
    
    ollama list
    
    echo ""
    echo -e "${BLUE}Required models for this project:${RESET}"
    echo "  Chat:      $CHAT_MODEL"
    echo "  Embedding: $EMBEDDING_MODEL"
}

cmd_clean() {
    echo -e "${YELLOW}This will remove all Ollama models. Continue? [y/N]${RESET}"
    read -r confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}Removing all models...${RESET}"
        
        for model in $(ollama list | tail -n +2 | awk '{print $1}'); do
            echo "Removing: $model"
            ollama rm "$model" 2>/dev/null || true
        done
        
        echo -e "${GREEN}✓ All models removed${RESET}"
    else
        echo "Cancelled"
    fi
}

cmd_logs() {
    if [ -f /tmp/ollama.log ]; then
        tail -f /tmp/ollama.log
    else
        echo "No log file found. Ollama may not have been started via this script."
    fi
}

cmd_help() {
    print_header
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  status    Check if Ollama is running and list models"
    echo "  start     Start Ollama server in background"
    echo "  stop      Stop Ollama server"
    echo "  pull      Pull required models (chat + embedding)"
    echo "  test      Test Ollama connection and models"
    echo "  models    List installed models"
    echo "  clean     Remove all models"
    echo "  logs      Tail Ollama logs"
    echo "  help      Show this help"
    echo ""
    echo "Environment variables:"
    echo "  OLLAMA_MODEL           Chat model (default: qwen2.5:32b)"
    echo "  OLLAMA_EMBEDDING_MODEL Embedding model (default: nomic-embed-text)"
    echo ""
}

# Main
check_ollama

case "${1:-help}" in
    status)  cmd_status ;;
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    pull)    cmd_pull ;;
    test)    cmd_test ;;
    models)  cmd_models ;;
    clean)   cmd_clean ;;
    logs)    cmd_logs ;;
    help|*)  cmd_help ;;
esac
