# Frontend (Next.js) Makefile
.PHONY: help install dev build start lint format clean

# Colors
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

PORT ?= 3000

help:
	@echo -e "$(BLUE)Agentic AI - Frontend (Next.js)$(RESET)"
	@echo ""
	@echo "Commands:"
	@echo "  make install   - Install dependencies"
	@echo "  make dev       - Start development server"
	@echo "  make build     - Build for production"
	@echo "  make start     - Start production server"
	@echo "  make lint      - Run linter"
	@echo "  make format    - Format code"
	@echo "  make clean     - Clean build artifacts"
	@echo "  make ui-add    - Add shadcn/ui component"
	@echo ""

# Installation
install:
	pnpm install

install-frozen:
	pnpm install --frozen-lockfile

# Development
dev:
	@echo -e "$(BLUE)Starting frontend on port $(PORT)...$(RESET)"
	pnpm dev --port $(PORT)

# Production
build:
	@echo -e "$(BLUE)Building for production...$(RESET)"
	pnpm build

start:
	@echo -e "$(BLUE)Starting production server on port $(PORT)...$(RESET)"
	pnpm start --port $(PORT)

# Linting & Formatting
lint:
	pnpm lint

lint-fix:
	pnpm lint --fix

format:
	pnpm prettier --write .

type-check:
	pnpm tsc --noEmit

# Code Quality (all checks)
check: lint type-check
	@echo -e "$(GREEN)All checks passed!$(RESET)"

# Clean
clean:
	rm -rf .next
	rm -rf out
	rm -rf node_modules
	rm -rf .turbo
	rm -f tsconfig.tsbuildinfo
	@echo -e "$(GREEN)Cleaned!$(RESET)"

clean-cache:
	rm -rf .next
	rm -rf .turbo
	@echo -e "$(GREEN)Cache cleaned!$(RESET)"

# shadcn/ui helpers
ui-add:
	@if [ -z "$(COMPONENT)" ]; then \
		echo -e "$(YELLOW)Usage: make ui-add COMPONENT=<name>$(RESET)"; \
		echo "Example: make ui-add COMPONENT=dialog"; \
		exit 1; \
	fi
	pnpm dlx shadcn-ui@latest add $(COMPONENT)

ui-list:
	@echo "Available shadcn/ui components:"
	@echo "  accordion, alert, alert-dialog, aspect-ratio, avatar, badge,"
	@echo "  breadcrumb, button, calendar, card, carousel, chart, checkbox,"
	@echo "  collapsible, combobox, command, context-menu, data-table, date-picker,"
	@echo "  dialog, drawer, dropdown-menu, form, hover-card, input, input-otp,"
	@echo "  label, menubar, navigation-menu, pagination, popover, progress,"
	@echo "  radio-group, resizable, scroll-area, select, separator, sheet,"
	@echo "  sidebar, skeleton, slider, sonner, switch, table, tabs, textarea,"
	@echo "  toast, toggle, toggle-group, tooltip"
