import React, { useRef, useState } from 'react'
import { Upload, X, Image as ImageIcon, AlertCircle } from 'lucide-react'

const MAX_SIZE_MB = 10
const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png']

export default function ImageUploader({ onFileSelect, disabled }) {
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState(null)
  const [preview, setPreview] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const inputRef = useRef(null)

  const validateAndSet = (file) => {
    setError(null)
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError('Only JPG, JPEG and PNG files are supported.')
      return
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`File must be smaller than ${MAX_SIZE_MB} MB.`)
      return
    }
    const url = URL.createObjectURL(file)
    setPreview(url)
    setSelectedFile(file)
    onFileSelect(file)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) validateAndSet(file)
  }

  const handleChange = (e) => {
    const file = e.target.files[0]
    if (file) validateAndSet(file)
  }

  const handleReset = () => {
    setPreview(null)
    setSelectedFile(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
    onFileSelect(null)
  }

  if (preview) {
    return (
      <div className="relative">
        <img
          src={preview}
          alt="Selected"
          className="w-full max-h-72 object-contain rounded-xl border border-gray-200 bg-gray-50"
        />
        <button
          onClick={handleReset}
          disabled={disabled}
          className="absolute top-2 right-2 w-8 h-8 bg-white rounded-full shadow-md flex items-center justify-center text-gray-500 hover:text-red-500 hover:bg-red-50 transition-colors"
          aria-label="Remove image"
        >
          <X size={16} />
        </button>
        <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
          <ImageIcon size={13} />
          <span>{selectedFile?.name}</span>
          <span>({(selectedFile?.size / 1024 / 1024).toFixed(2)} MB)</span>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors duration-200 ${
          dragOver
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <Upload size={32} className="mx-auto text-gray-400 mb-3" />
        <p className="text-sm font-medium text-gray-700">
          Drop an image here, or <span className="text-blue-600">browse</span>
        </p>
        <p className="text-xs text-gray-400 mt-1">JPG, JPEG, PNG · Max {MAX_SIZE_MB} MB</p>
        <input
          ref={inputRef}
          type="file"
          accept=".jpg,.jpeg,.png"
          className="hidden"
          onChange={handleChange}
          disabled={disabled}
        />
      </div>

      {error && (
        <div className="mt-2 flex items-center gap-2 text-sm text-red-600">
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}
