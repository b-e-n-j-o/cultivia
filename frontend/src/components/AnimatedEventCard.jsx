import React, { useEffect, useState } from 'react';

const AnimatedEventCard = ({ children, index }) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Délai progressif basé sur l'index pour un effet cascade
    const timeout = setTimeout(() => {
      setIsVisible(true);
    }, 150 * index); // Délai augmenté à 150ms

    return () => clearTimeout(timeout);
  }, [index]);

  // Styles pour l'animation
  const animationStyles = {
    opacity: isVisible ? 1 : 0,
    transform: isVisible ? 'translateY(0)' : 'translateY(20px)',
    transition: 'all 1s cubic-bezier(0.4, 0, 0.2, 1)', // Durée augmentée à 1s
  };

  return (
    <div
      style={animationStyles}
      className="will-change-transform"
    >
      {children}
    </div>
  );
};

export default AnimatedEventCard;