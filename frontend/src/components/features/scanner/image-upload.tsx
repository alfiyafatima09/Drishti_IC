/**
 * Image Upload Component
 * Handles file selection and preview for IC scanning
 */

'use client';

import { useRef, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Upload, Loader2 } from 'lucide-react';
import { validateImageFile } from '@/utils/validation';
import { useToast } from '@/hooks/use-toast';

interface ImageUploadProps {
  onFileSelect: (file: File, preview: string) => void;
  onUploadAndAnalyze: () => void;
  isUploading: boolean;
  isAnalyzing: boolean;
  preview: string | null;
  file: File | null;
}

export function ImageUpload({
  onFileSelect,
  onUploadAndAnalyze,
  isUploading,
  isAnalyzing,
  preview,
  file,
}: ImageUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    const validation = validateImageFile(selectedFile);
    if (!validation.valid) {
      toast({
        title: 'Invalid File',
        description: validation.error,
        variant: 'destructive',
      });
      return;
    }

    const reader = new FileReader();
    reader.onloadend = () => {
      onFileSelect(selectedFile, reader.result as string);
    };
    reader.readAsDataURL(selectedFile);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Upload Image</CardTitle>
        <CardDescription>Select an IC image from your device</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="file-upload">Image File</Label>
          <Input
            id="file-upload"
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            ref={fileInputRef}
            className="cursor-pointer"
            disabled={isUploading || isAnalyzing}
          />
        </div>

        {preview && (
          <div className="relative aspect-video bg-muted rounded-lg overflow-hidden">
            <img
              src={preview}
              alt="Preview"
              className="w-full h-full object-contain"
            />
          </div>
        )}

        <Button
          onClick={onUploadAndAnalyze}
          disabled={!file || isUploading || isAnalyzing}
          className="w-full"
        >
          {isUploading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Uploading...
            </>
          ) : isAnalyzing ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              Upload & Analyze
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}

