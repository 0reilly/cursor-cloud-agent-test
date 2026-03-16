#!/usr/bin/env ruby

require 'spaceship'
require 'spaceship/connect_api'

# Authenticate
key_id = ENV['APP_STORE_CONNECT_API_KEY_ID']
issuer_id = ENV['APP_STORE_CONNECT_API_ISSUER_ID']
key_path = ENV['APP_STORE_CONNECT_API_KEY_PATH'] || './AuthKey_KD23YKH5K8.p8'
key_content = File.read(File.expand_path(key_path))

Spaceship::ConnectAPI.auth(
  key_id: key_id,
  issuer_id: issuer_id,
  key: key_content
)

# Get first app
apps = Spaceship::ConnectAPI::App.all
if apps && !apps.empty?
  app = apps.first
  puts "First app: #{app.bundle_id} - #{app.name}"
  puts "App methods: #{app.methods.grep(/team|id|bundle|name|version/).sort}"
  
  # Try to inspect app attributes
  puts "\nApp attributes:"
  app.instance_variables.each do |var|
    puts "  #{var}: #{app.instance_variable_get(var)}"
  end
  
  # Check if there's a team_id attribute
  if app.respond_to?(:team_id)
    puts "Team ID from app: #{app.team_id}"
  end
  
  # Try to get app info with more details
  puts "\nTrying to get app with more details..."
  # Spaceship::ConnectAPI::App.get(id: app.id) might have more info
end

# Try different approach: maybe we need to use Spaceship.client
puts "\n\nChecking Spaceship.client..."
if defined?(Spaceship.client)
  puts "Spaceship.client: #{Spaceship.client}"
  if Spaceship.client.respond_to?(:team_id)
    puts "Team ID from client: #{Spaceship.client.team_id}"
  end
end

# Try to see what teams are available via Spaceship (Apple ID auth)
puts "\nTrying Spaceship.login (might need Apple ID)..."
# This will prompt for Apple ID password
# Skip for now
puts "Skipping Apple ID login"

# Check if we can get teams via API
puts "\nChecking for Team class..."
if defined?(Spaceship::ConnectAPI::Team)
  puts "Team class exists"
  teams = Spaceship::ConnectAPI::Team.all
  puts "Teams: #{teams.count}"
else
  puts "No Team class in ConnectAPI"
end

# Check Spaceship::Tunes which might have team info
puts "\nChecking Spaceship::Tunes..."
if defined?(Spaceship::Tunes)
  puts "Tunes module exists"
  # This requires Apple ID auth
end