variable "tenancy_ocid" {
  description = "OCIコンソール My Profile > API keys の Configuration file preview に表示されるtenancy OCID"
  type        = string
}

variable "user_ocid" {
  description = "OCIコンソール My Profile > API keys の Configuration file preview に表示されるuser OCID"
  type        = string
}

variable "fingerprint" {
  description = "OCI APIキーのfingerprint"
  type        = string
}

variable "private_key_path" {
  description = "OCI APIキーの秘密鍵ファイルパス(例: ~/.oci/oci_api_key.pem。Git管理外)"
  type        = string
}

variable "region" {
  description = "ホームリージョン"
  type        = string
  default     = "ap-osaka-1"
}

variable "compartment_ocid" {
  description = "リソースを作成するコンパートメントOCID(通常はtenancy_ocidと同じrootコンパートメント)"
  type        = string
}

variable "ssh_public_key_path" {
  description = "VMへのSSHログイン用公開鍵ファイルパス(例: ~/.ssh/smartcloset_vm.pub)"
  type        = string
}

variable "ssh_allowed_cidr" {
  description = "SSH(22番)接続を許可する自分のグローバルIPのCIDR表記(例: 203.0.113.10/32)"
  type        = string
}

variable "instance_ocpus" {
  description = "A1.FlexインスタンスのOCPU数(Out of Capacity時は減らしてリトライ)"
  type        = number
  default     = 4
}

variable "instance_memory_gbs" {
  description = "A1.Flexインスタンスのメモリ(GB)"
  type        = number
  default     = 24
}

variable "boot_volume_size_gbs" {
  description = "ブートボリュームサイズ(GB)"
  type        = number
  default     = 100
}
