# -*- mode: ruby -*-
# vi: set ft=ruby :

nodes = [
  { :hostname => 'source01', :ip => '192.168.56.42', :box => 'centos/7' },
  { :hostname => 'target01',  :ip => '192.168.56.43', :box => 'centos/7'}
]


Vagrant.configure("2") do |config|
  nodes.each do |node|
    config.vm.define node[:hostname] do |host|
      host.vm.box = node[:box]
      host.vm.hostname = node[:hostname]
      host.vm.network :private_network, ip: node[:ip]
    end
  end

  config.vm.provision "ansible" do |ansible|
    ansible.playbook = "playbook.yml"
  end
end

