'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Container } from '@/components/layout/container';
import { PageHeader } from '@/components/layout/page-header';
import { ImageUpload } from '@/components/features/scanner/image-upload';
import { AnalysisResults } from '@/components/features/scanner/analysis-results';
import { ApiService } from '@/services/api.service';
import { useToast } from '@/hooks/use-toast';

export default function ScannerPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<any>(null);
  const { toast } = useToast();
  const router = useRouter();

  const handleFileSelect = (selectedFile: File, previewUrl: string) => {
    setFile(selectedFile);
    setPreview(previewUrl);
    setResult(null);
  };

  const handleUploadAndAnalyze = async () => {
    if (!file) {
      toast({
        title: 'No File Selected',
        description: 'Please select an image file first',
        variant: 'destructive',
      });
      return;
    }

    setIsUploading(true);
    try {
      // Upload image
      const uploadResponse = await ApiService.image.uploadImage(file);

      toast({
        title: 'Upload Successful',
        description: 'Image uploaded successfully',
      });

      // Start analysis
      setIsAnalyzing(true);
      const analysisResponse = await ApiService.image.analyzeImage(uploadResponse.image_id);

      setResult(analysisResponse);
      toast({
        title: 'Analysis Complete',
        description: 'IC verification analysis completed',
      });
    } catch (error: any) {
      toast({
        title: 'Error',
        description: error.message || 'Failed to upload or analyze image',
        variant: 'destructive',
      });
    } finally {
      setIsUploading(false);
      setIsAnalyzing(false);
    }
  };

  const handleViewResult = () => {
    if (result?.verification_id) {
      router.push(`/results/${result.verification_id}`);
    }
  };

  return (
    <Container>
      <PageHeader
        title="IC Scanner"
        description="Upload or capture IC images for verification"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ImageUpload
          onFileSelect={handleFileSelect}
          onUploadAndAnalyze={handleUploadAndAnalyze}
          isUploading={isUploading}
          isAnalyzing={isAnalyzing}
          preview={preview}
          file={file}
        />

        <AnalysisResults
          result={result}
          onViewDetails={result?.verification_id ? handleViewResult : undefined}
        />
      </div>
    </Container>
  );
}
