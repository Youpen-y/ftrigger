#!/bin/bash
# Test script for event filter functionality

echo "=== Event Filter Test Script ==="
echo "Setting up test environment..."

# Clean up any previous test
rm -rf /tmp/ftrigger_test_created
rm -rf /tmp/ftrigger_test_modified
rm -rf /tmp/ftrigger_test_deleted
rm -rf /tmp/ftrigger_test_all

# Create test directories
mkdir -p /tmp/ftrigger_test_created
mkdir -p /tmp/ftrigger_test_modified
mkdir -p /tmp/ftrigger_test_deleted
mkdir -p /tmp/ftrigger_test_all

# Create test configuration
cat > /tmp/test_filter_config.yaml << 'EOF'
log_level: DEBUG

watches:
  # Test 1: Only monitor file creation
  - path: /tmp/ftrigger_test_created
    prompt: "✅ CREATED: {file}"
    recursive: false
    events: ["created"]
    extensions: [".test"]
    permission_mode: auto
    allowed_tools: ["Read"]

  # Test 2: Only monitor file modification
  - path: /tmp/ftrigger_test_modified
    prompt: "🔄 MODIFIED: {file}"
    recursive: false
    events: ["modified"]
    extensions: [".test"]
    permission_mode: auto
    allowed_tools: ["Read"]

  # Test 3: Only monitor file deletion
  - path: /tmp/ftrigger_test_deleted
    prompt: "🗑️  DELETED: {file}"
    recursive: false
    events: ["deleted"]
    extensions: [".test"]
    permission_mode: auto
    allowed_tools: ["Read"]

  # Test 4: Monitor all events
  - path: /tmp/ftrigger_test_all
    prompt: "📋 {event_type}: {file}"
    recursive: false
    events: ["created", "modified", "deleted", "moved"]
    extensions: [".test"]
    permission_mode: auto
    allowed_tools: ["Read"]
EOF

echo "Test configuration created: /tmp/test_filter_config.yaml"
echo ""
echo "Starting ftrigger with test configuration..."
echo "Run the following commands in another terminal to test:"
echo ""
echo "  # Test 1: Should trigger CREATED watch"
echo "  touch /tmp/ftrigger_test_created/test.test"
echo ""
echo "  # Test 2: Should trigger MODIFIED watch (create first, then modify)"
echo "  touch /tmp/ftrigger_test_modified/test.test"
echo "  echo 'content' >> /tmp/ftrigger_test_modified/test.test"
echo ""
echo "  # Test 3: Should trigger DELETED watch (create first, then delete)"
echo "  touch /tmp/ftrigger_test_deleted/test.test"
echo "  rm /tmp/ftrigger_test_deleted/test.test"
echo ""
echo "  # Test 4: Should trigger ALL event watches"
echo "  touch /tmp/ftrigger_test_all/test.test          # created"
echo "  echo 'content' >> /tmp/ftrigger_test_all/test.test  # modified"
echo "  mv /tmp/ftrigger_test_all/test.test /tmp/ftrigger_test_all/renamed.test  # moved"
echo "  rm /tmp/ftrigger_test_all/renamed.test          # deleted"
echo ""
echo "To stop ftrigger, press Ctrl+C"
echo ""

# Start ftrigger
python -m ftrigger --config /tmp/test_filter_config.yaml
