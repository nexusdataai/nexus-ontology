
import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';

// Temporary public token for development - in production this should be in an environment variable
const MAPBOX_TOKEN = 'pk.eyJ1IjoiZXhhbXBsZXVzZXIiLCJhIjoiY2xneGV6MHUzMDU1YTNwbTUzdzBvNDBvMiJ9.9yGJJbKVeAIGsqUBZMQxGQ';

interface MapComponentProps {
  className?: string;
}

const MapComponent: React.FC<MapComponentProps> = ({ className }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [mapLoaded, setMapLoaded] = useState(false);

  useEffect(() => {
    if (!mapContainer.current) return;

    // Initialize map
    mapboxgl.accessToken = MAPBOX_TOKEN;
    
    const mapInstance = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: [0, 30],
      zoom: 1.5,
    });

    // Add navigation controls
    mapInstance.addControl(
      new mapboxgl.NavigationControl(),
      'bottom-right'
    );

    // Set up event handlers
    mapInstance.on('load', () => {
      setMapLoaded(true);
    });

    map.current = mapInstance;

    // Clean up on unmount
    return () => {
      mapInstance.remove();
    };
  }, []);

  return (
    <div className={`relative h-full w-full ${className}`}>
      <div ref={mapContainer} className="absolute inset-0" />
    </div>
  );
};

export default MapComponent;
