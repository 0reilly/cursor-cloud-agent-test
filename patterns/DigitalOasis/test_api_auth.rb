#!/usr/bin/env ruby

require 'spaceship'

begin
  puts "Testing App Store Connect API authentication..."
  
  # Set up API key configuration - same as in Fastfile
  require 'spaceship/connect_api'
  
  Spaceship::ConnectAPI.configure do |config|
    config.key_id = ENV['APP_STORE_CONNECT_API_KEY_ID']
    config.issuer_id = ENV['APP_STORE_CONNECT_API_ISSUER_ID']
    config.key_filepath = ENV['APP_STORE_CONNECT_API_KEY_PATH']
  end
  
  puts "Key ID: #{ENV['APP_STORE_CONNECT_API_KEY_ID']}"
  puts "Issuer ID: #{ENV['APP_STORE_CONNECT_API_ISSUER_ID']}"
  puts "Key path: #{ENV['APP_STORE_CONNECT_API_KEY_PATH']}"
  
  # Test authentication by trying to create a token
  puts "Attempting to authenticate..."
  
  # Try to get a token - this will fail if credentials are invalid
  token = Spaceship::ConnectAPI.token
  if token
    puts "✅ Authentication successful!"
    puts "Token created successfully"
    
    # Try to fetch apps (might fail if no apps or insufficient permissions)
    begin
      apps = Spaceship::ConnectAPI::App.all
      puts "Found #{apps.count} apps in App Store Connect"
      apps.first(3).each do |app|
        puts "  - #{app.bundle_id}: #{app.name}"
      end
    rescue => e
      puts "Note: Could not fetch apps (may not have any or permissions limited): #{e.message}"
    end
  else
    puts "❌ Failed to create token"
  end
  
rescue Spaceship::AccessForbiddenError => e
  puts "❌ Authentication failed: Access Forbidden"
  puts "   The API key may not have sufficient permissions."
  puts "   Error: #{e.message}"
rescue Spaceship::UnexpectedResponse => e
  puts "❌ Authentication failed: Unexpected Response"
  puts "   Error: #{e.message}"
  puts "   Check your issuer ID and key permissions."
rescue => e
  puts "❌ Authentication failed with error: #{e.class.name}"
  puts "   Error: #{e.message}"
  puts "   Backtrace:" if e.backtrace
  e.backtrace.first(5).each { |line| puts "     #{line}" } if e.backtrace
end