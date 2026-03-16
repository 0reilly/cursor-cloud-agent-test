#!/usr/bin/env ruby

begin
  puts "Testing App Store Connect API authentication..."
  
  # Check if API key is configured
  unless ENV['APP_STORE_CONNECT_API_KEY_ID'] && ENV['APP_STORE_CONNECT_API_ISSUER_ID']
    puts "Error: App Store Connect API key not configured"
    exit 1
  end
  
  puts "Key ID: #{ENV['APP_STORE_CONNECT_API_KEY_ID']}"
  puts "Issuer ID: #{ENV['APP_STORE_CONNECT_API_ISSUER_ID']}"
  puts "Key path: #{ENV['APP_STORE_CONNECT_API_KEY_PATH']}"
  
  # Try to load spaceship
  require 'spaceship'
  
  # Try the authentication as done in Fastfile
  puts "Initializing Spaceship..."
  
  # This is the exact code from Fastfile line 102-107
  Spaceship::ConnectAPI.configure do |config|
    config.key_id = ENV['APP_STORE_CONNECT_API_KEY_ID']
    config.issuer_id = ENV['APP_STORE_CONNECT_API_ISSUER_ID']
    config.key_filepath = ENV['APP_STORE_CONNECT_API_KEY_PATH']
  end
  
  puts "Spaceship configured successfully"
  
  # Try to get a token
  puts "Testing token creation..."
  token = Spaceship::ConnectAPI.token
  puts "✅ Token created: #{token ? 'Yes' : 'No'}"
  
  # Try a simple API call
  puts "Testing API call..."
  begin
    # This is a simple API call that doesn't require an app
    # Try to get the current user
    user = Spaceship::ConnectAPI::User.all.first
    if user
      puts "✅ API call successful!"
      puts "   User: #{user.username}" if user.respond_to?(:username)
    else
      puts "⚠️  API call returned empty response (might be normal)"
    end
  rescue => e
    puts "⚠️  API call failed (may be normal without proper permissions): #{e.message}"
  end
  
  puts "\n✅ Authentication test completed!"
  
rescue LoadError => e
  puts "❌ Failed to load spaceship: #{e.message}"
  puts "Make sure Fastlane is installed: gem install fastlane"
rescue => e
  puts "❌ Authentication failed with error: #{e.class.name}"
  puts "   Error: #{e.message}"
  if e.backtrace
    puts "   Backtrace (first 3 lines):"
    e.backtrace.first(3).each { |line| puts "     #{line}" }
  end
end