
import React from "react";
import { Link } from "react-router-dom";
import ThemeToggle from "./ThemeToggle";

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  description: string;
  footer: {
    text: string;
    linkText: string;
    linkTo: string;
  };
}

export function AuthLayout({
  children,
  title,
  description,
  footer,
}: AuthLayoutProps) {
  return (
    <div className="min-h-screen w-full grid grid-cols-1 md:grid-cols-2 bg-background">
      {/* Left side branding panel */}
      <div className="hidden md:flex flex-col justify-between bg-sidebar p-8 relative">
        <div>
          <div className="flex items-center gap-2 mb-20">
            <div className="size-8 rounded-full bg-sidebar-primary flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
                <path d="M8 2c4 0 8 1.7 8 11 0 3.7-2.3 7-6 7-3 0-5-1.3-5-4 0-3.7 2-5 6-5 0 0 0 0 0 0"/>
              </svg>
            </div>
            <span className="font-semibold text-xl text-sidebar-foreground">Nexus AI</span>
          </div>
          <h1 className="text-4xl font-semibold text-sidebar-foreground mb-6">The intelligent AI operating layer for the enterprise</h1>
          <p className="text-lg text-sidebar-foreground/80 max-w-md">
            Connect your systems, build a verified ontology of your business, and deploy agents that reason and act.
          </p>
        </div>
        
        <div className="absolute bottom-8 right-8">
          <ThemeToggle />
        </div>
      </div>

      {/* Right side auth form */}
      <div className="flex flex-col justify-center items-center p-6 md:p-12">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center md:text-left mb-8">
            <h2 className="text-3xl font-semibold tracking-tight mb-2">{title}</h2>
            <p className="text-muted-foreground">{description}</p>
          </div>

          {children}

          <div className="text-center text-sm text-muted-foreground mt-6">
            {footer.text}{" "}
            <Link to={footer.linkTo} className="underline text-primary hover:text-primary/80 font-medium">
              {footer.linkText}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
