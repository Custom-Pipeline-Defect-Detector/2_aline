import React, { useState, useRef, useEffect } from 'react';
import { Card } from '../components/ui/Card';
import Button from '../components/ui/Button';
import Input from '../components/ui/Input';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  filePath?: string; // Optional property for file paths
  fileName?: string; // Optional property for file names
}

const AiAssistantPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'auto' }); // Changed to 'auto' for immediate scroll
  };

  useEffect(() => {
    const loadConversation = async () => {
      const sessionId = localStorage.getItem('ai-session-id');
      const token = localStorage.getItem('token');
      
      if (sessionId && token) {
        try {
          // Fetch existing messages from the session
          const response = await fetch(`/api/ai/sessions/${sessionId}/messages`, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          });
          
          if (response.ok) {
            const existingMessages = await response.json();
            // Convert API response to our Message format
            const formattedMessages = existingMessages.map((msg: any) => ({
              id: msg.id.toString(),
              content: msg.content,
              role: msg.role,
              timestamp: new Date(msg.created_at || Date.now())
            }));
            setMessages(formattedMessages);
            // Scroll to bottom after loading messages
            setTimeout(() => scrollToBottom(), 100); // Small delay to ensure DOM is updated
          }
        } catch (error) {
          console.error('Error loading conversation:', error);
        }
      } else {
        // Show initial welcome message if no session exists
        setMessages([{
          id: 'welcome',
          content: 'Hello! I\'m your AI assistant. How can I help you today?',
          role: 'assistant',
          timestamp: new Date(),
        }]);
        // Scroll to bottom for welcome message
        setTimeout(() => scrollToBottom(), 100);
      }
    };

    loadConversation();
  }, []);

  useEffect(() => {
    // Scroll to bottom whenever messages change
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      content: inputValue,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // First, we need to get or create a chat session
      let sessionId = localStorage.getItem('ai-session-id');
      const token: string | null = localStorage.getItem('token'); // Get token once and check if it exists
      
      if (!sessionId) {
        // Create a new session
        const sessionResponse = await fetch('/api/ai/sessions', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
          },
          body: JSON.stringify({ title: 'AI Assistant Conversation' }),
        });

        if (!sessionResponse.ok) {
          throw new Error(`Session creation failed: ${sessionResponse.statusText}`);
        }

        const sessionData = await sessionResponse.json();
        sessionId = sessionData.id;
        localStorage.setItem('ai-session-id', sessionId);
      }

      // Call the AI chat API with the session
      // Ensure sessionId is not null before using it in the URL
      if (!sessionId) {
        throw new Error('Session ID is required but was not created');
      }

      const response = await fetch(`/api/ai/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({ 
          message: inputValue,
          context: {}
        }),
      });

      if (!response.ok) {
        throw new Error(`AI response failed: ${response.statusText}`);
      }

      const data = await response.json();

      // Extract content and file path from the response
      let content = data.reply || data.response || 'No response from AI';
      let filePath: string | undefined;
      let fileName: string | undefined;

      // Check if the response contains a file path from the backend
      if (data.file_path) {
        filePath = data.file_path; // Full path like "uploads/filename.xlsx"
        const pathParts = data.file_path.split('/');
        fileName = pathParts[pathParts.length - 1]; // Just the filename like "filename.xlsx"
      } else {
        // Fallback to parsing the content for file paths (for backward compatibility)
        const filePathMatch = content.match(/uploads\/([^\s]+)/);
        if (filePathMatch) {
          filePath = filePathMatch[0]; // Full path like "uploads/filename.xlsx"
          fileName = filePathMatch[1]; // Just the filename like "filename.xlsx"
          // Remove the file path from the content to show cleaner message
          content = content.replace(filePathMatch[0], fileName);
        }
      }

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: content,
        role: 'assistant',
        timestamp: new Date(),
        filePath: filePath,
        fileName: fileName
      };

      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      console.error('Error getting AI response:', error);
      
      // Add error message
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I encountered an error. Please try again.',
        role: 'assistant',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-120px)] max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-slate-900">Automation AI Assistant</h1>
        <p className="text-slate-600 mt-2">Ask questions about automation development, projects, and data</p>
      </div>

      {/* Chat Container */}
      <Card className="flex-1 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-blue-500 text-white rounded-br-none'
                    : 'bg-slate-100 text-slate-800 rounded-bl-none'
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>
                {message.filePath && message.fileName && (
                  <div className="mt-2">
                    <a 
                      href={`/api/documents/download-excel/${message.fileName}`} 
                      download={message.fileName}
                      className="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                    >
                      Download {message.fileName}
                    </a>
                  </div>
                )}
                <div
                  className={`text-xs mt-1 ${
                    message.role === 'user' ? 'text-blue-200' : 'text-slate-500'
                  }`}
                >
                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-2xl rounded-bl-none bg-slate-100 text-slate-800 px-4 py-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce"></div>
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce delay-100"></div>
                  <div className="w-2 h-2 rounded-full bg-slate-400 animate-bounce delay-200"></div>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t border-slate-200 p-4">
          <div className="flex space-x-3">
            <Input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message here..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              className="px-6"
            >
              Send
            </Button>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            Ask about your documents, projects, customers, or any data in the system
          </p>
        </div>
      </Card>
    </div>
  );
};

export default AiAssistantPage;