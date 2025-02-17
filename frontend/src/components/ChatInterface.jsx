import { useState } from 'react';
import { Send } from 'lucide-react';

const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Ajouter le message de l'utilisateur
    const userMessage = { text: input, isUser: true };
    setMessages([...messages, userMessage]);

    try {
      console.log("Sending request to backend...");
      const response = await fetch('http://localhost:5003/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ message: input }) // Notez qu'on envoie juste input, pas userMessage
      });

      console.log("Response received:", response);
      const data = await response.json();
      console.log("Data received:", data);
      
      if (data.status === 'success') {
        const botMessage = {
          text: data.response,
          isUser: false
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        const errorMessage = {
          text: "Désolé, une erreur est survenue.",
          isUser: false
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error('Error details:', error);
      const errorMessage = {
        text: "Désolé, une erreur est survenue lors de la communication avec le serveur.",
        isUser: false
      };
      setMessages(prev => [...prev, errorMessage]);
    }

    setInput('');
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <div className="p-4 bg-white shadow">
        <h1 className="text-xl font-bold text-gray-800">LaVitrine Assistant</h1>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.isUser ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[70%] rounded-lg p-3 ${
                message.isUser
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-200 text-gray-800'
              }`}
            >
              {message.text.split('\n').map((line, i) => (
                <span key={i}>
                  {line}
                  {i !== message.text.split('\n').length - 1 && <br />}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="p-4 bg-white border-t">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Posez votre question sur les événements..."
            className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            className="p-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          >
            <Send size={20} />
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatInterface;