
import { useState } from "react";
import { LogOut, Settings, User } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "./ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import UserAvatar from "./UserAvatar";
import { useEnterpriseAuth } from "@/context/EnterpriseAuthContext";

const UserMenu = () => {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { user, profile, signOutUser, loading } = useEnterpriseAuth();

  const handleProfile = () => {
    setOpen(false);
    alert("Profile page - Coming soon! This would show user profile settings and information.");
  };

  const handleSettings = () => {
    setOpen(false);
    navigate('/settings');
  };

  const handleSignOut = async () => {
    setOpen(false);
    const confirmLogout = confirm("Are you sure you want to log out?");
    if (confirmLogout) {
      try {
        await signOutUser();
      } catch (error) {
        console.error("Logout error:", error);
      }
    }
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="ghost" 
          className="relative h-10 w-10 rounded-full p-0 border-none hover:bg-accent"
          aria-label="Open user menu"
        >
          <UserAvatar />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent 
        className="w-56 mt-2 bg-popover" 
        align="end" 
        sideOffset={15}
        forceMount
      >
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">
              {profile?.full_name || "User"}
            </p>
            <p className="text-xs leading-none text-muted-foreground">
              {profile?.email || "Loading..."}
            </p>
            {profile?.role && (
              <p className="text-xs leading-none text-muted-foreground font-medium">
                Role: {profile.role}
              </p>
            )}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem 
          onClick={handleSignOut} 
          className="cursor-pointer hover:bg-accent"
          disabled={loading}
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>{loading ? "Logging out..." : "Log out"}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export default UserMenu;
