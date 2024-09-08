import React from 'react';
import Image from 'next/image';

const GifDisplay = ({ gifPath, altText = 'GIF', width, height }) => {
  return (
    <div className="flex justify-center items-center my-8">
      <Image
        src={gifPath}
        alt={altText}
        width={width}
        height={height}
        className="rounded-lg shadow-lg"
        quality={100} // Ensures the image quality is high
      />
    </div>
  );
};

export default GifDisplay;
