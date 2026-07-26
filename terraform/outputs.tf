output "public_ip" {
    value = aws_instance.health_monitor.public_ip
}