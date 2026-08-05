output "instance_public_ip" {
  description = "VMのパブリックIPアドレス(DNS設定・SSH接続・health確認に使用)"
  value       = oci_core_instance.vm.public_ip
}
