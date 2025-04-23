import { useState, useRef, useEffect } from 'react';
import { Send, Smile, Moon, Sun, RefreshCw } from 'lucide-react';

export default function EnhancedChatBot() {
  const [messages, setMessages] = useState([
    { id: 1, text: "Hi there! I'm your friendly chatbot. How can I help you today?", sender: 'bot' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [theme, setTheme] = useState('light');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  
  const botResponses = [
    "That's interesting! Tell me more.",
    "How can I assist you further?",
    "I understand. Is there anything specific you're looking for?",
    "Great question! Let me think about that...",
    "I'm here to help with whatever you need.",
    "Could you elaborate on that?",
    "I appreciate your patience as I continue learning.",
    "That's a good point! Have you considered alternatives?",
    "I'm processing your request. Just a moment...",
    "Thanks for sharing that with me!"
  ];
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => {
    scrollToBottom();
    if (messages.length > 1) {
      inputRef.current?.focus();
    }
  }, [messages]);
  
  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() === '') return;
    
    // Add user message
    const newId = messages.length + 1;
    setMessages([...messages, { id: newId, text: input, sender: 'user' }]);
    setInput('');
    
    // Simulate bot typing
    setIsTyping(true);
    
    // Simulate bot response after a delay
    setTimeout(() => {
      setIsTyping(false);
      const randomResponse = botResponses[Math.floor(Math.random() * botResponses.length)];
      setMessages(prevMessages => [
        ...prevMessages, 
        { id: prevMessages.length + 1, text: randomResponse, sender: 'bot' }
      ]);
    }, 1000 + Math.random() * 1000);
  };
  
  const clearChat = () => {
    setMessages([
      { id: 1, text: "Hi there! I'm your friendly chatbot. How can I help you today?", sender: 'bot' }
    ]);
  };
  
  return (
    <div className={`flex flex-col h-screen ${theme === 'dark' ? 'bg-gray-900 text-gray-100' : 'bg-gray-50'} transition-colors duration-300`}>
      <div className={`p-4 ${theme === 'dark' ? 'bg-violet-900' : 'bg-violet-600'} text-white shadow-lg transition-colors duration-300`}>
        <div className="max-w-3xl mx-auto flex justify-between items-center">
          <h1 className="text-2xl font-bold flex items-center">
            <span className="mr-2">🤖</span>
            <span className="animate-pulse">Interactive Chatbot</span>
          </h1>
          <div className="flex space-x-3">
            <button 
              onClick={clearChat} 
              className="p-2 rounded-full hover:bg-violet-700 transition-colors duration-200"
              title="Clear chat"
            >
              <RefreshCw size={20} />
            </button>
            <button 
              onClick={toggleTheme} 
              className="p-2 rounded-full hover:bg-violet-700 transition-colors duration-200"
              title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            >
              {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
            </button>
          </div>
        </div>
      </div>
      
      <div className={`flex-1 overflow-y-auto p-4 ${theme === 'dark' ? 'bg-gray-800' : 'bg-gray-100'} transition-colors duration-300`}>
        <div className="max-w-3xl mx-auto">
          {messages.map((message, index) => (
            <div 
              key={message.id} 
              className={`my-3 animate-fadeIn ${index === messages.length - 1 ? 'animate-slideIn' : ''}`}
              style={{ 
                animationDelay: `${index * 0.1}s`,
                opacity: 0,
                animation: `fadeIn 0.5s ease-out ${index * 0.1}s forwards${
                  index === messages.length - 1 ? `, slideIn 0.5s ease-out ${index * 0.1}s` : ''
                }`
              }}
            >
              <div className={`p-3 rounded-lg max-w-xs lg:max-w-md ${
                message.sender === 'user' 
                  ? 'ml-auto bg-gradient-to-r from-blue-500 to-violet-500 text-white shadow-md' 
                  : `mr-auto ${theme === 'dark' ? 'bg-gray-700' : 'bg-white'} shadow-md`
              } transition-all duration-300 hover:shadow-lg`}>
                <p>{message.text}</p>
              </div>
              <div className={`mt-1 text-xs ${
                message.sender === 'user' ? 'text-right mr-2' : 'ml-2'
              } ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
                {message.sender === 'user' ? 'You' : 'Bot'} • Just now
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="my-3 animate-fadeIn">
              <div className={`p-3 rounded-lg inline-block mr-auto ${theme === 'dark' ? 'bg-gray-700' : 'bg-white'} shadow-md`}>
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-violet-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                  <div className="w-2 h-2 bg-violet-600 rounded-full animate-bounce" style={{animationDelay: '0.4s'}}></div>
                </div>
              </div>
              <div className={`mt-1 text-xs ml-2 ${theme === 'dark' ? 'text-gray-400' : 'text-gray-500'}`}>
                Bot is typing...
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
      
      <form 
        onSubmit={handleSubmit} 
        className={`p-4 ${theme === 'dark' ? 'bg-gray-900' : 'bg-white'} shadow-lg transition-colors duration-300`}
      >
        <div className="max-w-3xl mx-auto">
          <div className={`flex items-center rounded-full overflow-hidden ${
            theme === 'dark' ? 'bg-gray-800 border-gray-700' : 'bg-gray-100 border-gray-300'
          } border focus-within:ring-2 focus-within:ring-violet-500 transition-all duration-300 hover:shadow-md`}>
            <button 
              type="button" 
              className={`p-3 ${theme === 'dark' ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'} transition-colors duration-200`}
            >
              <Smile size={20} />
            </button>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message here..."
              className={`flex-1 p-3 ${
                theme === 'dark' ? 'bg-gray-800 text-white placeholder-gray-500' : 'bg-gray-100 text-gray-800 placeholder-gray-400'
              } focus:outline-none transition-colors duration-300`}
            />
            <button 
              type="submit" 
              className={`p-3 ${
                input.trim() === '' 
                  ? 'text-gray-400' 
                  : 'text-violet-500 hover:text-violet-600'
              } transition-colors duration-200 transform ${
                input.trim() !== '' ? 'hover:scale-110' : ''
              }`}
              disabled={input.trim() === ''}
            >
              <Send size={20} className={input.trim() !== '' ? 'animate-pulse' : ''} />
            </button>
          </div>
        </div>
      </form>
      
      <style jsx global>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        @keyframes slideIn {
          from { transform: translateY(10px); }
          to { transform: translateY(0); }
        }
        
        .animate-fadeIn {
          opacity: 0;
          animation: fadeIn 0.5s ease-out forwards;
        }
        
        .animate-slideIn {
          animation: slideIn 0.5s ease-out;
        }
      `}</style>
    </div>
  );
}