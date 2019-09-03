$ssh_pub_key = File.readlines("#{Dir.home}/.ssh/id_rsa.pub").first.strip

$script = <<-SCRIPT
set -e
sudo bash -c "echo #{$ssh_pub_key} >> /home/vagrant/.ssh/authorized_keys"
SCRIPT

Vagrant.configure("2") do |config|
  config.vm.provider "virtualbox" do |v|
    v.memory = 2048
  end

  config.vm.define "vm1" do |cfg|
    cfg.vm.box = "centos/7"
    cfg.vm.network "private_network", ip: "172.19.0.2"
    cfg.vm.hostname = 'vm1'
  end

  config.vm.define "vm2" do |cfg|
    cfg.vm.box = "centos/7"
    cfg.vm.network "private_network", ip: "172.19.0.3"
    cfg.vm.hostname = 'vm2'
  end

  config.vm.provision :shell, inline: $script
end
