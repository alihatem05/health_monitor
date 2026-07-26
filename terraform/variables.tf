variable "region" {
  type        = string
  default     = "eu-north-1" # Stockholm — check it's still in your free tier eligibility
}

variable "instance_type" {
  type        = string
  default     = "t3.micro" # free-tier eligible on most accounts; t2.micro on older accounts
}

variable "key_pair" {
  type        = string
}

variable "ip" {
  type        = string
}

variable "port" {
  type        = number
  default     = 8000
}

variable "docker_image" {
  type        = string
}