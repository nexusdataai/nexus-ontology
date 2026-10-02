
import React from 'react';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

interface UserAvatarProps {
  className?: string;
  onClick?: () => void;
}

const UserAvatar: React.FC<UserAvatarProps> = ({ className, onClick }) => {
  // Mock user data
  const mockUser = {
    fullName: "Demo User"
  };
  
  // Get the first letter of the user's name for the avatar
  const getInitial = () => {
    if (mockUser.fullName) {
      return mockUser.fullName.charAt(0).toUpperCase();
    }
    return "A";
  };

  return (
    <Avatar 
      className={cn("h-10 w-10 bg-secondary border border-border cursor-pointer", className)}
      onClick={onClick}
    >
      <AvatarFallback className="text-foreground">{getInitial()}</AvatarFallback>
    </Avatar>
  );
};

export default UserAvatar;
