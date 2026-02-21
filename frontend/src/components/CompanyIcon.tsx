import React, { useState } from 'react';
import { Avatar } from '@mui/material';

interface CompanyIconProps {
  website?: string | null;
  name: string;
  size?: number;
}

const CompanyIcon: React.FC<CompanyIconProps> = ({ website, name, size = 24 }) => {
  const [imgError, setImgError] = useState(false);

  const faviconUrl = website && !imgError
    ? `https://www.google.com/s2/favicons?domain=${website}&sz=32`
    : null;

  const initial = name.charAt(0).toUpperCase();

  if (faviconUrl) {
    return (
      <Avatar
        src={faviconUrl}
        alt={name}
        onError={() => setImgError(true)}
        sx={{ width: size, height: size, fontSize: size * 0.5 }}
        variant="rounded"
      >
        {initial}
      </Avatar>
    );
  }

  return (
    <Avatar
      sx={{
        width: size,
        height: size,
        fontSize: size * 0.5,
        bgcolor: 'primary.main',
      }}
      variant="rounded"
    >
      {initial}
    </Avatar>
  );
};

export default CompanyIcon;
