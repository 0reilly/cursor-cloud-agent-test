#!/usr/bin/env ruby

require 'spaceship'
require 'spaceship/connect_api'

puts "Testing Spaceship::ConnectAPI.auth method..."
puts "Method arity: #{Spaceship::ConnectAPI.method(:auth).arity}"

# Try to call with different parameters
# Based on Fastlane source, might be:
# Spaceship::ConnectAPI.auth(key_id: ..., issuer_id: ..., key: ...)
# or Spaceship::ConnectAPI.auth(key_id: ..., issuer_id: ..., key_filepath: ...)

key_id = ENV['APP_STORE_CONNECT_API_KEY_ID']
issuer_id = ENV['APP_STORE_CONNECT_API_ISSUER_ID']
key_filepath = ENV['APP_STORE_CONNECT_API_KEY_PATH']

puts "Key ID: #{key_id}"
puts "Issuer ID: #{issuer_id}"
puts "Key file path: #{key_filepath}"

# Read key file
key_content = File.read(key_filepath) if File.exist?(key_filepath)
puts "Key content length: #{key_content.length}" if key_content

begin
  puts "\nTrying auth with key_id, issuer_id, key_filepath..."
  # Try with key_filepath
  token = Spaceship::ConnectAPI.auth(key_id: key_id, issuer_id: issuer_id, key_filepath: key_filepath)
  puts "✅ Auth succeeded with key_filepath!"
  puts "Token: #{token ? 'Present' : 'Nil'}"
rescue => e
  puts "❌ Auth with key_filepath failed: #{e.class.name}: #{e.message}"
end

begin
  puts "\nTrying auth with key_id, issuer_id, key (content)..."
  # Try with key content
  token = Spaceship::ConnectAPI.auth(key_id: key_id, issuer_id: issuer_id, key: key_content)
  puts "✅ Auth succeeded with key content!"
  puts "Token: #{token ? 'Present' : 'Nil'}"
rescue => e
  puts "❌ Auth with key content failed: #{e.class.name}: #{e.message}"
end

begin
  puts "\nTrying Spaceship::ConnectAPI.login (might be for Apple ID)..."
  # This might be for Apple ID password auth
  token = Spaceship::ConnectAPI.login
  puts "✅ Login succeeded (might be using cached token)"
  puts "Token: #{token ? 'Present' : 'Nil'}"
rescue => e
  puts "❌ Login failed: #{e.class.name}: #{e.message}"
end

# Try to get token directly
puts "\nTrying to get token..."
if Spaceship::ConnectAPI.token
  puts "✅ Token exists: #{Spaceship::ConnectAPI.token ? 'Yes' : 'No'}"
else
  puts "⚠️  No token exists yet"
end