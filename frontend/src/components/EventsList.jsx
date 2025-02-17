import { useState } from 'react';
import AnimatedEventCard from './AnimatedEventCard';

const EventCard = ({ event, index, onToggleExpand, isExpanded }) => {
  const [isDateExpanded, setIsDateExpanded] = useState(false);
  
  const handleDateToggle = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDateExpanded(!isDateExpanded);
  };

  const formatDate = (date, time) => {
    return `${date} à ${time || ''}`;
  };

  const renderDates = () => {
    if (!event.date) return null;

    // Si c'est un tableau de dates
    if (Array.isArray(event.date) && event.date.length > 0) {
      const sortedDates = [...event.date].map((date, idx) => ({
        date,
        time: Array.isArray(event.time) ? event.time[idx] : event.time
      })).sort((a, b) => new Date(a.date) - new Date(b.date));

      const maxVisibleDates = isDateExpanded ? sortedDates.length : 2;
      const hasMoreDates = sortedDates.length > 2;

      return (
        <div className="mt-2">
          <div className="flex items-center gap-2">
            <span className="text-gray-600">🗓</span>
            <div className="flex-1">
              {sortedDates.slice(0, maxVisibleDates).map((dateObj, idx) => (
                <div key={idx} className="text-gray-600">
                  {formatDate(dateObj.date, dateObj.time)}
                </div>
              ))}
              {hasMoreDates && !isDateExpanded && (
                <button
                  onClick={handleDateToggle}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium mt-1"
                >
                  Voir {sortedDates.length - 2} autres dates...
                </button>
              )}
              {hasMoreDates && isDateExpanded && (
                <button
                  onClick={handleDateToggle}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium mt-1"
                >
                  Afficher moins
                </button>
              )}
            </div>
          </div>
        </div>
      );
    }

    // Si c'est une seule date
    return (
      <p className="text-gray-600">
        🗓 {formatDate(event.date, event.time)}
      </p>
    );
  };

  const renderDisciplines = () => {
    if (!event.discipline) return null;
    
    const disciplines = Array.isArray(event.discipline) 
      ? event.discipline.join(', ')
      : event.discipline;

    return (
      <p className="text-gray-600">
        🎭 {disciplines}
      </p>
    );
  };

  const cardContent = (
    <div className="flex flex-col space-y-2">
      {/* En-tête avec titre et score */}
      <div className="flex justify-between items-start">
        <h3 className="font-bold text-lg flex-1 pr-4">{event.title || 'Sans titre'}</h3>
        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm whitespace-nowrap">
          {((event.score || 0) * 100).toFixed(1)}%
        </span>
      </div>

      {/* Informations de l'événement */}
      <div className="space-y-2">
        {renderDates()}
        {renderDisciplines()}
        <p className="text-gray-600">
          📍 {event.venue || ''}{event.city ? ` à ${event.city}` : ''}
        </p>
      </div>

      {/* Description avec bouton "voir plus" */}
      {event.description && (
        <div className="mt-2">
          <p className={`text-gray-700 text-sm ${isExpanded ? '' : 'line-clamp-3'}`}>
            {event.description}
          </p>
          {event.description.length > 150 && (
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onToggleExpand(index);
              }}
              className="text-blue-600 hover:text-blue-800 text-sm font-medium mt-1"
            >
              {isExpanded ? 'Afficher moins' : 'Afficher plus'}
            </button>
          )}
        </div>
      )}
    </div>
  );

  return (
    <a
      href={event.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block bg-white border rounded-lg p-4 hover:shadow-md transition-all duration-200 hover:bg-blue-50 cursor-pointer"
    >
      {cardContent}
    </a>
  );
};

const EventsList = ({ events, isLoading }) => {
  const [expandedCards, setExpandedCards] = useState({});
  const [visibleEvents, setVisibleEvents] = useState(5);

  const handleToggleExpand = (index) => {
    setExpandedCards(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const handleLoadMore = () => {
    setVisibleEvents(prev => prev + 5);
  };

  const hasMoreEvents = visibleEvents < events.length;

  const containerClasses = "bg-white rounded-lg shadow-lg p-6";
  const contentClasses = "h-[600px] overflow-y-auto space-y-4 pr-2";

  if (isLoading) {
    return (
      <div className={containerClasses}>
        <div className={contentClasses}>
          <div className="h-full flex flex-col items-center justify-center">
            <div className="w-8 h-8 border-t-2 border-blue-500 rounded-full animate-spin mb-4"></div>
            <p className="text-gray-600 font-medium">Chargement de vos événements...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={containerClasses}>
      <h2 className="text-2xl font-bold mb-4">
        Événements trouvés ({events.length})
      </h2>
      
      <div className="space-y-4">
        <div className={contentClasses}>
          {events.slice(0, visibleEvents).map((event, index) => (
            <AnimatedEventCard 
              key={event.id || index} 
              // On commence l'index à -1 pour que le premier élément soit pris en compte
              index={index - 1}
            >
              <EventCard 
                event={event}
                index={index}
                isExpanded={expandedCards[index]}
                onToggleExpand={() => handleToggleExpand(index)}
              />
            </AnimatedEventCard>
          ))}
        </div>
        
        {hasMoreEvents && (
          <div className="flex justify-center mt-4">
            <button
              onClick={handleLoadMore}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 
                       transition-colors duration-200"
            >
              Voir plus d'événements
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default EventsList;