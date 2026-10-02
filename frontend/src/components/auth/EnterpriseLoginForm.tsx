import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, Mail, Lock, Building2, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { useEnterpriseAuth } from "@/context/EnterpriseAuthContext";

// Schema for Cognito login
const cognitoLoginSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address" }),
  password: z.string().min(6, { message: "Password must be at least 6 characters" }),
});

type CognitoLoginFormValues = z.infer<typeof cognitoLoginSchema>;

interface EnterpriseLoginFormProps {
  onSuccess?: () => void;
  onError?: (error: Error) => void;
  defaultTab?: 'adfs' | 'cognito';
  showTabSwitcher?: boolean;
  className?: string;
}

export const EnterpriseLoginForm: React.FC<EnterpriseLoginFormProps> = ({
  onSuccess,
  onError,
  defaultTab = 'adfs',
  showTabSwitcher = true,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState(defaultTab);
  const [showPassword, setShowPassword] = useState(false);
  
  const { 
    signInWithADFS, 
    signInWithCognito, 
    loading 
  } = useEnterpriseAuth();

  // Cognito form handling
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    clearErrors
  } = useForm<CognitoLoginFormValues>({
    resolver: zodResolver(cognitoLoginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const handleADFSLogin = async () => {
    try {
      clearErrors();
      await signInWithADFS();
      onSuccess?.();
    } catch (error) {
      console.error('ADFS login error:', error);
      onError?.(error as Error);
    }
  };

  const handleCognitoLogin = async (data: CognitoLoginFormValues) => {
    try {
      clearErrors();
      await signInWithCognito(data.email, data.password);
      onSuccess?.();
    } catch (error) {
      console.error('Cognito login error:', error);
      onError?.(error as Error);
    }
  };

  const isLoading = loading || isSubmitting;

  return (
    <div className={`w-full max-w-md mx-auto ${className}`}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Welcome Back</CardTitle>
          <CardDescription>
            Sign in to access the Nexus AI
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {showTabSwitcher ? (
            <Tabs value={activeTab} onValueChange={setActiveTab as any} className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="adfs" className="flex items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  Corporate SSO
                </TabsTrigger>
                <TabsTrigger value="cognito" className="flex items-center gap-2">
                  <User className="h-4 w-4" />
                  Direct Login
                </TabsTrigger>
              </TabsList>
              
              {/* ADFS/SSO Login Tab */}
              <TabsContent value="adfs" className="space-y-4">
                <Alert>
                  <Building2 className="h-4 w-4" />
                  <AlertDescription>
                    Use your corporate credentials to sign in through Active Directory.
                  </AlertDescription>
                </Alert>
                
                <div className="space-y-4">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground mb-4">
                      Click below to authenticate with your corporate account
                    </p>
                  </div>
                  
                  <Button
                    onClick={handleADFSLogin}
                    disabled={isLoading}
                    className="w-full"
                    size="lg"
                  >
                    {isLoading ? (
                      "Redirecting to SSO..."
                    ) : (
                      <>
                        <Building2 className="mr-2 h-5 w-5" />
                        Sign in with Corporate SSO
                      </>
                    )}
                  </Button>
                  
                  <div className="text-center">
                    <p className="text-xs text-muted-foreground">
                      You will be redirected to your organization's login page
                    </p>
                  </div>
                </div>
              </TabsContent>
              
              {/* Cognito Direct Login Tab */}
              <TabsContent value="cognito" className="space-y-4">
                <Alert>
                  <User className="h-4 w-4" />
                  <AlertDescription>
                    Sign in directly with your Nexus AI account.
                  </AlertDescription>
                </Alert>
                
                <form onSubmit={handleSubmit(handleCognitoLogin)} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                      <Input
                        id="email"
                        type="email"
                        placeholder="you@company.com"
                        className="pl-10"
                        {...register("email")}
                        disabled={isLoading}
                      />
                    </div>
                    {errors.email && (
                      <p className="text-sm text-destructive">{errors.email.message}</p>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                      <Input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        placeholder="••••••••••••"
                        className="pl-10 pr-10"
                        {...register("password")}
                        disabled={isLoading}
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                        onClick={() => setShowPassword(!showPassword)}
                        disabled={isLoading}
                      >
                        {showPassword ? (
                          <EyeOff className="h-5 w-5" />
                        ) : (
                          <Eye className="h-5 w-5" />
                        )}
                      </button>
                    </div>
                    {errors.password && (
                      <p className="text-sm text-destructive">{errors.password.message}</p>
                    )}
                  </div>
                  
                  <Button
                    type="submit"
                    disabled={isLoading}
                    className="w-full"
                    size="lg"
                  >
                    {isLoading ? "Signing in..." : "Sign In"}
                  </Button>
                </form>
                
                <div className="text-center">
                  <Button
                    variant="link"
                    className="text-sm text-muted-foreground hover:text-foreground"
                    onClick={() => {
                      // Handle forgot password - would integrate with Cognito
                      console.log('Forgot password clicked');
                    }}
                  >
                    Forgot your password?
                  </Button>
                </div>
              </TabsContent>
            </Tabs>
          ) : (
            // Single login method when tabs are disabled
            <div className="space-y-4">
              {defaultTab === 'adfs' ? (
                <>
                  <Alert>
                    <Building2 className="h-4 w-4" />
                    <AlertDescription>
                      Use your corporate credentials to sign in.
                    </AlertDescription>
                  </Alert>
                  
                  <Button
                    onClick={handleADFSLogin}
                    disabled={isLoading}
                    className="w-full"
                    size="lg"
                  >
                    {isLoading ? (
                      "Redirecting to SSO..."
                    ) : (
                      <>
                        <Building2 className="mr-2 h-5 w-5" />
                        Sign in with Corporate SSO
                      </>
                    )}
                  </Button>
                </>
              ) : (
                <form onSubmit={handleSubmit(handleCognitoLogin)} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                      <Input
                        id="email"
                        type="email"
                        placeholder="you@company.com"
                        className="pl-10"
                        {...register("email")}
                        disabled={isLoading}
                      />
                    </div>
                    {errors.email && (
                      <p className="text-sm text-destructive">{errors.email.message}</p>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                      <Input
                        id="password"
                        type={showPassword ? "text" : "password"}
                        placeholder="••••••••••••"
                        className="pl-10 pr-10"
                        {...register("password")}
                        disabled={isLoading}
                      />
                      <button
                        type="button"
                        className="absolute right-3 top-2.5 text-muted-foreground hover:text-foreground"
                        onClick={() => setShowPassword(!showPassword)}
                        disabled={isLoading}
                      >
                        {showPassword ? (
                          <EyeOff className="h-5 w-5" />
                        ) : (
                          <Eye className="h-5 w-5" />
                        )}
                      </button>
                    </div>
                    {errors.password && (
                      <p className="text-sm text-destructive">{errors.password.message}</p>
                    )}
                  </div>
                  
                  <Button
                    type="submit"
                    disabled={isLoading}
                    className="w-full"
                    size="lg"
                  >
                    {isLoading ? "Signing in..." : "Sign In"}
                  </Button>
                </form>
              )}
            </div>
          )}
          
          <div className="mt-6">
            <Separator className="my-4" />
            <div className="text-center">
              <p className="text-xs text-muted-foreground">
                Having trouble signing in? Contact your IT administrator.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default EnterpriseLoginForm;
