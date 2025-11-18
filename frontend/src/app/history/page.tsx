'use client';

import { useEffect, useState } from 'react';
import { apiRequest } from '@/api/client';
import { API_ENDPOINTS } from '@/lib/config';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle, Loader2, Eye, RefreshCw } from 'lucide-react';
import { useRouter } from 'next/navigation';

export default function HistoryPage() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();
  const router = useRouter();

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const data = await apiRequest<any[]>(API_ENDPOINTS.verificationHistory);
      setHistory(data || []);
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to load history',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [toast]);

  if (loading) {
    return (
      <div className="container mx-auto p-6 flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Verification History</h1>
          <p className="text-muted-foreground">View all past IC verification results</p>
        </div>
        <Button variant="outline" onClick={fetchHistory}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {history.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="text-center py-12">
              <p className="text-muted-foreground">No verification history found</p>
              <p className="text-sm text-muted-foreground mt-2">
                Start verifying ICs to see results here
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {history.map((item) => (
            <Card key={item.verification_id} className="hover:shadow-md transition-shadow">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-3">
                      {item.is_genuine ? (
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600" />
                      )}
                      <div>
                        <h3 className="font-semibold">
                          {item.part_number || 'Unknown Part Number'}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {item.manufacturer || 'Unknown Manufacturer'}
                        </p>
                      </div>
                      <Badge variant={item.is_genuine ? 'default' : 'destructive'}>
                        {item.is_genuine ? 'Genuine' : 'Counterfeit'}
                      </Badge>
                    </div>

                    {item.confidence && (
                      <div className="flex items-center gap-4 text-sm">
                        <span className="text-muted-foreground">Confidence:</span>
                        <span className="font-medium">
                          {(item.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                    )}

                    {item.created_at && (
                      <p className="text-xs text-muted-foreground">
                        {new Date(item.created_at).toLocaleString()}
                      </p>
                    )}
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push(`/results/${item.verification_id}`)}
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    View Details
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

