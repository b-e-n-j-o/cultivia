import React, { useState, useEffect } from 'react';

const ChatMessage = ({ message, isLoading }) => {
  const isUser = message.type === 'user';
  const [visibleParagraphs, setVisibleParagraphs] = useState([]);
  
  useEffect(() => {
    // Nettoyer et dédupliquer les paragraphes
    const uniqueParagraphs = [...new Set(
      message.content
        .split('\n')
        .map(p => p.trim())
        .filter(p => p !== '')
    )];

    if (!isUser) {
      setVisibleParagraphs([]); // Reset initial
      let currentIndex = -1;
      
      const showNextParagraph = () => {
        if (currentIndex < uniqueParagraphs.length) {
          setVisibleParagraphs(prev => [...prev, uniqueParagraphs[currentIndex]]);
          currentIndex++;
          setTimeout(showNextParagraph, 800);
        }
      };
      
      const timer = setTimeout(showNextParagraph, 100);
      return () => clearTimeout(timer);
    } else {
      setVisibleParagraphs(uniqueParagraphs);
    }
  }, [message.content, isUser]);

  return (
    <div className="mb-4 w-full animate-message-appear">
      <div className={`
        w-full p-4 rounded-lg
        ${isUser ? 'bg-blue-600 text-white' : 'bg-gray-100'}
      `}>
        {isUser ? (
          <div className="whitespace-pre-wrap">
            {message.content}
          </div>
        ) : (
          <div className="space-y-4">
            {visibleParagraphs.map((paragraph, index) => (
              <p 
                key={`${message.id}-${index}`}
                className="animate-paragraph-appear opacity-0"
                style={{
                  animationDelay: `${index * 0.1}s`,
                  animationFillMode: 'forwards'
                }}
              >
                {paragraph}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const LoadingIndicator = () => (
  <div className="w-full mb-4 animate-fade-in">
    <div className="bg-gray-100 rounded-lg p-4">
      <div className="flex items-center space-x-2">
        <div className="w-3 h-3 bg-gray-400 rounded-full animate-bounce" />
        <div className="w-3 h-3 bg-gray-400 rounded-full animate-bounce delay-150" />
        <div className="w-3 h-3 bg-gray-400 rounded-full animate-bounce delay-300" />
      </div>
    </div>
  </div>
);

export default function MessagesContainer({ messages, isLoading }) {
  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <ChatMessage key={message.id} message={message} />
      ))}
      {isLoading && <LoadingIndicator />}
    </div>
  );
}