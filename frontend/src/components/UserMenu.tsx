import { useState } from "react";
import { Icon } from "@/components/ds/Icon";
import { useNavigate } from "react-router-dom";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "./ui/alert-dialog";
import { Badge } from "./ui/badge";
import { useEnterpriseAuth } from "@/context/EnterpriseAuthContext";

const initialsOf = (name?: string | null, email?: string | null) => {
  const src = (name || email || "").trim();
  if (!src) return "U";
  const parts = src.split(/[\s._@-]+/).filter(Boolean);
  return ((parts[0]?.[0] || "") + (parts.length > 1 ? parts[1][0] : "")).toUpperCase() || "U";
};

const UserMenu = () => {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const navigate = useNavigate();
  const { profile, signOutUser, loading } = useEnterpriseAuth();

  const handleSignOut = async () => {
    try {
      await signOutUser();
    } catch (error) {
      console.error("Logout error:", error);
    }
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            aria-label="Open user menu"
            className="flex h-8 w-8 items-center justify-center rounded-full border border-border-strong bg-surface-2 text-xs font-medium text-foreground transition-colors duration-200 hover:border-brand/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {initialsOf(profile?.full_name, profile?.email)}
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-60" align="end" sideOffset={8}>
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col gap-1">
              <p className="truncate text-sm font-medium leading-none">{profile?.full_name || "User"}</p>
              <p className="truncate text-xs leading-none text-muted-foreground">{profile?.email || "Loading…"}</p>
              {profile?.role && (
                <Badge variant="neutral" className="mt-1.5 w-fit">{profile.role}</Badge>
              )}
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => navigate("/settings")} className="cursor-pointer">
            <Icon name="settings" className="mr-2" />
            <span>Settings</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setConfirmOpen(true)} className="cursor-pointer" disabled={loading}>
            <Icon name="logout" className="mr-2" />
            <span>{loading ? "Logging out…" : "Log out"}</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Log out of Nexus AI?</AlertDialogTitle>
            <AlertDialogDescription>You will need to sign in again to continue.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleSignOut}>Log out</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default UserMenu;
