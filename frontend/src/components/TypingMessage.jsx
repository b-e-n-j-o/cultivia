import React, { useState, useEffect, useRef } from 'react';

const TypingMessage = ({ content }) => {
  const [displayedParagraphs, setDisplayedParagraphs] = useState([]);
  const [isTyping, setIsTyping] = useState(true);
  const contentRef = useRef(content);

  useEffect(() => {
    // Réinitialiser l'état quand un nouveau contenu arrive
    contentRef.current = content;
    setDisplayedParagraphs([]);
    setIsTyping(true);

    if (!content) return;

    // Séparer le contenu en paragraphes
    const paragraphs = content.split('\n').filter(p => p.trim() !== '');
    let currentParagraphIndex = -1;

    const typingInterval = setInterval(() => {
      if (currentParagraphIndex < paragraphs.length) {
        setDisplayedParagraphs(prev => [...prev, paragraphs[currentParagraphIndex]]);
        currentParagraphIndex++;
      } else {
        setIsTyping(false);
        clearInterval(typingInterval);
      }
    }, 600); // Délai entre chaque paragraphe (ajustable)

    return () => clearInterval(typingInterval);
  }, [content]);

  if (!content) return null;

  return (
    <div className="whitespace-pre-wrap space-y-4">
      {displayedParagraphs.map((paragraph, index) => (
        <p key={index} className="animate-fade-in">
          {paragraph}
        </p>
      ))}
      {isTyping && (
        <span className="inline-block animate-pulse ml-1"></span>
      )}
    </div>
  );
};

// Ajout de l'animation de fade-in pour les paragraphes
const styles = `
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .animate-fade-in {
    animation: fadeIn 0.5s ease-out forwards;
  }
`;

// Injecter les styles dans le document
const styleSheet = document.createElement("style");
styleSheet.innerText = styles;
document.head.appendChild(styleSheet);

export default TypingMessage;