#!/usr/bin/env ruby

require 'spaceship'
require 'spaceship/connect_api'

begin
  puts "Fetching team information from App Store Connect API..."
  
  # Check environment
  unless ENV['APP_STORE_CONNECT_API_KEY_ID'] && ENV['APP_STORE_CONNECT_API_ISSUER_ID']
    puts "Error: API credentials not set in environment"
    exit 1
  end
  
  key_id = ENV['APP_STORE_CONNECT_API_KEY_ID']
  issuer_id = ENV['APP_STORE_CONNECT_API_ISSUER_ID']
  key_path = ENV['APP_STORE_CONNECT_API_KEY_PATH'] || './AuthKey_KD23YKH5K8.p8'
  
  puts "Key ID: #{key_id}"
  puts "Issuer ID: #{issuer_id}"
  puts "Key path: #{key_path}"
  
  # Read key
  key_content = File.read(File.expand_path(key_path))
  
  # Authenticate
  puts "\nAuthenticating..."
  token = Spaceship::ConnectAPI.auth(
    key_id: key_id,
    issuer_id: issuer_id,
    key: key_content
  )
  
  puts "✅ Authentication successful!"
  puts "Token: #{token ? 'Present' : 'Nil'}"
  
  # Try to get user info
  puts "\nFetching user information..."
  users = Spaceship::ConnectAPI::User.all
  if users && !users.empty?
    user = users.first
    puts "Current user: #{user.username}" if user.respond_to?(:username)
    puts "User ID: #{user.id}" if user.respond_to?(:id)
    puts "Email: #{user.email}" if user.respond_to?(:email)
  else
    puts "No user information available"
  end
  
  # Try to get apps (will fail if none exist)
  puts "\nFetching apps..."
  apps = Spaceship::ConnectAPI::App.all
  puts "Found #{apps.count} apps"
  apps.each do |app|
    puts "  - #{app.bundle_id}: #{app.name} (#{app.app_store_state})"
  end
  
  # Try to get teams (might need different API)
  puts "\nTrying to get team information..."
  # Spaceship::ConnectAPI::Team might exist
  if defined?(Spaceship::ConnectAPI::Team)
    teams = Spaceship::ConnectAPI::Team.all
    puts "Found #{teams.count} teams"
    teams.each do |team|
      puts "  - Team ID: #{team.id}, Name: #{team.name}" if team.respond_to?(:name)
    end
  else
    puts "Spaceship::ConnectAPI::Team class not found"
  end
  
  # Alternative: Try to use older Spaceship API
  puts "\nTrying older Spaceship API for team info..."
  begin
    # This might work for Apple ID auth, not API key
    # But let's try
    if Spaceship.respond_to?(:select_team)
      puts "Spaceship.select_team exists"
    end
  rescue => e
    puts "Older API not available: #{e.message}"
  end
  
  # Check what methods are available on token
  puts "\nAvailable methods on token:"
  if token
    puts token.methods.grep(/team|group|org/).sort
  end
  
rescue => e
  puts "❌ Error: #{e.class.name}: #{e.message}"
  if e.backtrace
    puts "Backtrace (first 3):"
    e.backtrace.first(3).each { |line| puts "  #{line}" }
  end
end