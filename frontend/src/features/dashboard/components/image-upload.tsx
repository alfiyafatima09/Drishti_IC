import { useCallback, useState } from 'react'
import type { RefObject } from 'react'
import { Upload, Image as ImageIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ImageUploadProps {
  onFileSelect: (files: File[]) => void
  fileInputRef: RefObject<HTMLInputElement | null>
  disabled?: boolean
  title?: string
  multiple?: boolean
  acceptFolders?: boolean
}

export function ImageUpload({
  onFileSelect,
  fileInputRef,
  disabled,
  title,
  multiple = false,
  acceptFolders = false,
}: ImageUploadProps) {
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
        const maxFiles = multiple ? (acceptFolders ? 100 : 2) : 1

        for (let i = 0; i < Math.min(files.length, maxFiles); i++) {
          const file = files[i]
          if (acceptFolders) {
            // Accept images and ZIP files
            if (file.type.startsWith('image/') || file.name.toLowerCase().endsWith('.zip')) {
              validFiles.push(file)
            }
          } else if (file.type.startsWith('image/')) {
            validFiles.push(file)
          }
        }

        if (validFiles.length > 0) {
          onFileSelect(validFiles)
        }
      }
    },
    [onFileSelect, disabled, multiple],
  )

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files
      if (files && files.length > 0) {
        const validFiles: File[] = []
        const maxFiles = multiple ? (acceptFolders ? 100 : 2) : 1

        for (let i = 0; i < Math.min(files.length, maxFiles); i++) {
          const file = files[i]
          if (acceptFolders) {
            // Accept images and ZIP files
            if (file.type.startsWith('image/') || file.name.toLowerCase().endsWith('.zip')) {
              validFiles.push(file)
            }
          } else if (file.type.startsWith('image/')) {
            validFiles.push(file)
          }
        }

        onFileSelect(validFiles)
      }
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    },
    [onFileSelect, fileInputRef, multiple, acceptFolders],
  )

  const handleClick = useCallback(() => {
    if (!disabled) {
      fileInputRef.current?.click()
    }
  }, [fileInputRef, disabled])

  return (
    <div className="w-full">
      {title && (
        <div className="mb-3">
          <h4 className="text-sm font-medium text-gray-700">{title}</h4>
        </div>
      )}
      <input
        ref={fileInputRef}
        type="file"
        accept={acceptFolders ? 'image/*,.zip' : 'image/*'}
        multiple={multiple}
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
            {isDragging
              ? `Drop ${acceptFolders ? 'files/folders' : multiple ? 'images' : 'image'} here`
              : `Click or drag ${acceptFolders ? 'images, ZIP folders, or select multiple files' : multiple ? 'up to 2 images' : 'image'} to upload`}
          </p>
          <p className="text-muted-foreground text-xs">
            {acceptFolders ? 'JPG, PNG, or ZIP (max 50MB total)' : 'JPG or PNG (max 10MB)'}
          </p>
        </div>
      </div>
    </div>
  )
}
