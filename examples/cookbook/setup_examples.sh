#!/bin/bash
# Setup script for cookbook examples

echo "🚀 Setting up Arcade cookbook examples..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p examples/cookbook/using_local_resources/workspace
mkdir -p examples/cookbook/using_local_resources/cache
mkdir -p examples/cookbook/notetaker_local_mcp/notes

# Copy environment files
echo "📋 Setting up environment files..."
if [ -f "examples/cookbook/using_local_resources/env.example" ]; then
    if [ ! -f "examples/cookbook/using_local_resources/.env" ]; then
        cp examples/cookbook/using_local_resources/env.example examples/cookbook/using_local_resources/.env
        echo "  ✓ Created .env for using_local_resources"
    fi
fi

if [ -f "examples/cookbook/gmail_curator/env.example" ]; then
    if [ ! -f "examples/cookbook/gmail_curator/.env" ]; then
        cp examples/cookbook/gmail_curator/env.example examples/cookbook/gmail_curator/.env
        echo "  ✓ Created .env for gmail_curator"
    fi
fi

# Create sample files for testing
echo "📄 Creating sample files..."
echo "This is a sample document for testing." > examples/cookbook/using_local_resources/workspace/sample.txt
echo "Another test file." > examples/cookbook/using_local_resources/workspace/test.txt

# Set permissions
echo "🔐 Setting permissions..."
chmod 755 examples/cookbook/using_local_resources/workspace
chmod 755 examples/cookbook/using_local_resources/cache
chmod 755 examples/cookbook/notetaker_local_mcp/notes

# Remove empty placeholder directories
echo "🧹 Cleaning up empty directories..."
for dir in using_deployed_tools using_cursor using_claude agent_memory_mcp_http; do
    if [ -d "examples/cookbook/$dir" ] && [ -z "$(ls -A examples/cookbook/$dir)" ]; then
        rmdir "examples/cookbook/$dir"
        echo "  ✓ Removed empty $dir"
    fi
done

echo ""
echo "✅ Setup complete! You can now run the tests:"
echo ""
echo "  cd examples/cookbook"
echo "  python test_all_examples.py"
echo ""
echo "Or test individual examples:"
echo ""
echo "  cd examples/cookbook/simple_tool"
echo "  arcade serve"