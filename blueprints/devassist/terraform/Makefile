# DevAssist Blueprint - Terraform Makefile

.PHONY: init plan apply destroy fmt validate clean

ENV ?= local
CONFIG_DIR = config/$(ENV)
TFVARS = $(CONFIG_DIR)/tfvars.conf

# Colors
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

help:
	@echo -e "$(BLUE)DevAssist Blueprint - Terraform$(RESET)"
	@echo ""
	@echo "Usage: make <target> [ENV=local|dev|staging|prod]"
	@echo ""
	@echo "Targets:"
	@echo "  init      Initialize Terraform"
	@echo "  plan      Plan infrastructure changes"
	@echo "  apply     Apply infrastructure changes"
	@echo "  destroy   Destroy infrastructure"
	@echo "  fmt       Format Terraform files"
	@echo "  validate  Validate Terraform configuration"
	@echo "  output    Show Terraform outputs"
	@echo "  clean     Clean Terraform state"
	@echo ""
	@echo "Current ENV: $(ENV)"

init:
	@echo -e "$(BLUE)Initializing Terraform...$(RESET)"
	terraform init

plan:
	@echo -e "$(BLUE)Planning with ENV=$(ENV)...$(RESET)"
	@if [ -f "$(TFVARS)" ]; then \
		terraform plan -var-file=$(TFVARS); \
	else \
		echo -e "$(YELLOW)Warning: No tfvars file found at $(TFVARS), using defaults$(RESET)"; \
		terraform plan; \
	fi

apply:
	@echo -e "$(BLUE)Applying with ENV=$(ENV)...$(RESET)"
	@if [ -f "$(TFVARS)" ]; then \
		terraform apply -var-file=$(TFVARS) -auto-approve; \
	else \
		echo -e "$(YELLOW)Warning: No tfvars file found at $(TFVARS), using defaults$(RESET)"; \
		terraform apply -auto-approve; \
	fi
	@echo -e "$(GREEN)Infrastructure deployed!$(RESET)"

destroy:
	@echo -e "$(YELLOW)Destroying infrastructure for ENV=$(ENV)...$(RESET)"
	@if [ -f "$(TFVARS)" ]; then \
		terraform destroy -var-file=$(TFVARS) -auto-approve; \
	else \
		terraform destroy -auto-approve; \
	fi

fmt:
	terraform fmt -recursive

validate:
	terraform validate

output:
	terraform output -json

clean:
	@echo -e "$(YELLOW)Cleaning Terraform state...$(RESET)"
	rm -rf .terraform
	rm -f .terraform.lock.hcl
	rm -f terraform.tfstate*
