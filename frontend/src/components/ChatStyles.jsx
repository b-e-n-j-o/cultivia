import React from 'react';

const ChatStyles = () => {
  return (
    <style>
      {`
        @keyframes messageAppear {
          0% {
            opacity: 0;
            transform: translateY(20px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes paragraphAppear {
          0% {
            opacity: 0;
            transform: translateY(10px);
          }
          100% {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes fadeIn {
          0% {
            opacity: 0;
          }
          100% {
            opacity: 1;
          }
        }

        .animate-message-appear {
          animation: messageAppear 0.5s ease-out forwards;
        }

        .animate-paragraph-appear {
          animation: paragraphAppear 0.5s ease-out forwards;
        }

        .animate-fade-in {
          animation: fadeIn 0.3s ease-out forwards;
        }

        .delay-150 {
          animation-delay: 0.15s;
        }

        .delay-300 {
          animation-delay: 0.3s;
        }

        /* Ajustements pour le container de messages */
        .messages-container {
          padding: 1rem;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        /* Style des messages */
        .message {
          width: 100%;
          transition: all 0.3s ease;
        }

        /* Animation du typing indicator */
        .typing-indicator {
          display: inline-flex;
          gap: 0.5rem;
        }
      `}
    </style>
  );
};

export default ChatStyles;