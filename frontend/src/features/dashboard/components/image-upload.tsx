import { useCallback, useState } from 'react'
import type { RefObject } from 'react'
import { Upload, Image as ImageIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ImageUploadProps {
  onFilesSelect: (files: File[]) => void
  fileInputRef: RefObject<HTMLInputElement | null>
  disabled?: boolean
}

export function ImageUpload({ onFilesSelect, fileInputRef, disabled }: ImageUploadProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragEnter = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      if (!disabled) setIsDragging(true)
    },
    [disabled],
  )

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setIsDragging(false)

      if (disabled) return

      const files = e.dataTransfer.files
      if (files && files.length > 0) {
        const validFiles: File[] = []
        // Limit to first 2 files
        const count = Math.min(files.length, 2)

        for (let i = 0; i < count; i++) {
          if (files[i].type.startsWith('image/')) {
            validFiles.push(files[i])
          }
        }

        if (validFiles.length > 0) {
          onFilesSelect(validFiles)
        }
      }
    },
    [onFilesSelect, disabled],
  )

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        const validFiles: File[] = []
        // Limit to first 2 files
        const count = Math.min(files.length, 2)

        for (let i = 0; i < count; i++) {
          validFiles.push(files[i])
        }

        onFilesSelect(validFiles)
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    },
    [onFilesSelect, fileInputRef],
  )

  const handleClick = useCallback(() => {
    if (!disabled) {
      fileInputRef.current?.click()
    }
  }, [fileInputRef, disabled])

  return (
    <div className="w-full">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        onChange={handleFileChange}
        className="hidden"
      />

      <div
        onClick={handleClick}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        className={cn(
          'relative flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-12 text-center transition-colors',
          isDragging
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-muted/50',
          disabled && 'cursor-not-allowed opacity-50',
        )}
      >
        <div className="bg-muted mb-4 rounded-full p-4">
          {isDragging ? (
            <Upload className="text-primary h-6 w-6" />
          ) : (
            <ImageIcon className="text-muted-foreground h-6 w-6" />
          )}
        </div>
        <div className="space-y-1">
          <p className="text-foreground text-sm font-medium">
            {isDragging ? 'Drop images here' : 'Click or drag up to 2 images to upload'}
          </p>
          <p className="text-muted-foreground text-xs">JPG or PNG (max 10MB)</p>
        </div>
      </div>
    </div>
  )
}
