import { useState, useRef, useEffect } from 'react';
import EventsList from './EventsList';
import MessagesContainer from './ChatMessage';
import ChatStyles from './ChatStyles';

const EventSearch = () => {
  const [messages, setMessages] = useState([]);
  const [events, setEvents] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);
  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const chatContainerRef = useRef(null);

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, isLoadingChat]);

  const searchEvents = async (input) => {
    setIsLoadingEvents(true);
    try {
      const searchResponse = await fetch('http://localhost:5003/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      });

      const searchData = await searchResponse.json();
      
      if (searchData.events && Array.isArray(searchData.events)) {
        const processedEvents = searchData.events.map(event => ({
          ...event,
          url: event.url || (event.metadata && event.metadata.event_url) || ''
        }));
        
        setEvents(processedEvents);
        return { 
          promptEvents: searchData.prompt_events || [], 
          targetDate: searchData.target_date 
        };
      }
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsLoadingEvents(false);
    }
  };

  const getChatResponse = async (input, promptEvents, targetDate) => {
    setIsLoadingChat(true);
    try {
      const chatResponse = await fetch('http://localhost:5003/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,
          prompt_events: promptEvents,
          target_date: targetDate
        }),
      });

      const chatData = await chatResponse.json();
      
      if (chatData.message) {
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          type: 'system',
          content: chatData.message.replace(/([H])\1+/g, '')
        }]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        id: Date.now().toString(),
        type: 'system',
        content: "Désolé, une erreur s'est produite lors de la génération de la réponse."
      }]);
    } finally {
      setIsLoadingChat(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!userInput.trim()) return;

    setMessages(prev => [...prev, {
      id: Date.now().toString(),
      type: 'user',
      content: userInput
    }]);

    const currentInput = userInput;
    setUserInput('');

    const searchResult = await searchEvents(currentInput);
    if (searchResult) {
      getChatResponse(currentInput, searchResult.promptEvents, searchResult.targetDate);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <ChatStyles />
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Section Chat */}
          <div className="bg-white rounded-lg shadow-lg p-6">
            <h2 className="text-2xl font-bold mb-4">Chat</h2>
            
            <div 
              ref={chatContainerRef}
              className="h-[600px] overflow-y-auto mb-4 bg-white rounded-lg p-4"
            >
              <MessagesContainer 
                messages={messages}
                isLoading={isLoadingChat}
              />
            </div>

            <form onSubmit={handleSubmit} className="flex gap-2">
              <input
                type="text"
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                placeholder="Décrivez ce que vous recherchez comme événement..."
                className="flex-1 p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                disabled={isLoadingEvents && isLoadingChat}
              />
              <button
                type="submit"
                disabled={isLoadingEvents && isLoadingChat}
                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                         disabled:bg-blue-300 transition-colors"
              >
                Envoyer
              </button>
            </form>
          </div>

          {/* Section Événements */}
          <EventsList events={events} isLoading={isLoadingEvents} />
        </div>
      </div>
    </div>
  );
};

export default EventSearch;