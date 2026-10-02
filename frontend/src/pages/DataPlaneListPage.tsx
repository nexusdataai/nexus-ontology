import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { dataPlaneService, DataPlane } from '@/services/dataPlaneService';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog';
import { Plus, Eye, Trash2, Database, ArrowLeft } from 'lucide-react';
import Layout from '@/components/Layout';

const typeBadgeColor: Record<string, string> = {
  FDW: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  CDC: 'bg-green-500/20 text-green-400 border-green-500/30',
  ETL: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
};

const statusColor: Record<string, string> = {
  connected: 'bg-green-500',
  disconnected: 'bg-gray-500',
  error: 'bg-red-500',
  pending: 'bg-yellow-500',
};

export default function DataPlaneListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { data: planes = [], isLoading } = useQuery({
    queryKey: ['data-planes'],
    queryFn: () => dataPlaneService.list(),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => dataPlaneService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['data-planes'] });
      setDeleteId(null);
    },
  });

  return (
    <Layout>
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <Database className="h-6 w-6" />
          <h1 className="text-2xl font-semibold">Data Planes</h1>
        </div>
        <Button onClick={() => navigate('/data-plane/create')}>
          <Plus className="h-4 w-4 mr-2" /> Create Data Plane
        </Button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">Loading...</p>
      ) : planes.length === 0 ? (
        <div className="text-center py-16">
          <Database className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <h2 className="text-lg font-medium mb-2">No data planes configured</h2>
          <p className="text-muted-foreground mb-4">Create your first data plane to connect to enterprise data sources.</p>
          <Button onClick={() => navigate('/data-plane/create')}>
            <Plus className="h-4 w-4 mr-2" /> Create Data Plane
          </Button>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {planes.map((dp: DataPlane) => (
              <TableRow key={dp.id}>
                <TableCell className="font-medium">{dp.name}</TableCell>
                <TableCell>
                  <Badge variant="outline" className={typeBadgeColor[dp.type] || ''}>
                    {dp.type}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span className={`h-2 w-2 rounded-full ${statusColor[dp.status] || 'bg-gray-500'}`} />
                    {dp.status}
                  </div>
                </TableCell>
                <TableCell>{new Date(dp.createdAt).toLocaleDateString()}</TableCell>
                <TableCell className="text-right">
                  <Button variant="ghost" size="icon" onClick={() => navigate(`/data-plane/${dp.id}`)}>
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => setDeleteId(dp.id)}>
                    <Trash2 className="h-4 w-4 text-red-400" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Data Plane?</AlertDialogTitle>
            <AlertDialogDescription>This action cannot be undone.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteId && deleteMutation.mutate(deleteId)}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
    </Layout>
  );
}
