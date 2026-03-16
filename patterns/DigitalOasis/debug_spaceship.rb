#!/usr/bin/env ruby

require 'spaceship'

puts "Spaceship version: #{Spaceship::VERSION}" if defined?(Spaceship::VERSION)
puts "Spaceship::ConnectAPI class: #{Spaceship::ConnectAPI}"
puts "Methods: #{Spaceship::ConnectAPI.methods.grep(/configure|auth|login|token/).sort}"

# Check if ConnectAPI has a singleton class
puts "\nChecking ConnectAPI singleton class..."
puts "Singleton methods: #{Spaceship::ConnectAPI.singleton_methods.grep(/configure|auth|login|token/).sort}"

# Check ancestors
puts "\nAncestors: #{Spaceship::ConnectAPI.ancestors}"

# Try to require spaceship/connect_api
begin
  require 'spaceship/connect_api'
  puts "\nSuccessfully required spaceship/connect_api"
  puts "After require - methods: #{Spaceship::ConnectAPI.methods.grep(/configure|auth|login|token/).sort}"
rescue LoadError => e
  puts "\nCould not load spaceship/connect_api: #{e.message}"
end

# Try to find token method
puts "\nLooking for token method..."
if Spaceship::ConnectAPI.respond_to?(:token)
  puts "Spaceship::ConnectAPI.token exists"
else
  puts "Spaceship::ConnectAPI.token does not exist"
end

# Try Spaceship.login maybe?
puts "\nChecking Spaceship class methods: #{Spaceship.methods.grep(/login|auth/).sort}"