'use client';

import { useParams } from 'next/navigation';
import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Upload,
  FileText,
  Trash2,
  Database,
  Search,
  AlertCircle,
  CheckCircle2,
  Loader2,
  FolderOpen,
  File,
  CheckSquare,
  Square,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  uploadDocument,
  listDocuments,
  listScopes,
  deleteDocument,
  deleteScope,
  searchDocuments,
  type ScopeInfo,
  type DocumentSearchResult,
  type DocumentResponse,
} from '@/lib/api/rag';

const SUPPORTED_EXTENSIONS = [
  '.txt',
  '.md',
  '.py',
  '.js',
  '.ts',
  '.tsx',
  '.jsx',
  '.json',
  '.yaml',
  '.yml',
];

export default function KnowledgePage() {
  const params = useParams();
  const blueprint = params.blueprint as string;

  const [scopeInfo, setScopeInfo] = useState<ScopeInfo | null>(null);
  const [currentScope, setCurrentScope] = useState<string>('default');
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteDocDialogOpen, setDeleteDocDialogOpen] = useState(false);
  const [bulkDeleteDialogOpen, setBulkDeleteDialogOpen] = useState(false);
  const [scopeToDelete, setScopeToDelete] = useState<string | null>(null);
  const [docToDelete, setDocToDelete] = useState<{ id: string; filename: string } | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<DocumentSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);

  const loadScopes = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listScopes();
      setScopeInfo(data);
      
      // Set default scope if it exists, otherwise use first available
      if (data.scopes.length > 0) {
        if (!data.scopes.includes(currentScope)) {
          setCurrentScope(data.scopes[0]);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load scopes');
    } finally {
      setLoading(false);
    }
  }, [currentScope]);

  const loadDocuments = useCallback(async (scope: string) => {
    try {
      setLoadingDocs(true);
      const data = await listDocuments(scope, 100);
      setDocuments(data.documents);
      // Clear selection when loading new scope
      setSelectedFiles(new Set());
    } catch (err) {
      console.error('Failed to load documents:', err);
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    loadScopes();
  }, [loadScopes]);

  useEffect(() => {
    if (currentScope) {
      loadDocuments(currentScope);
    }
  }, [currentScope, loadDocuments]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        await handleUpload(files[0]);
      }
    },
    [currentScope]
  );

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await handleUpload(files[0]);
    }
  };

  const handleUpload = async (file: File) => {
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();
    
    if (!SUPPORTED_EXTENSIONS.includes(fileExt)) {
      setError(`Unsupported file type: ${fileExt}. Supported: ${SUPPORTED_EXTENSIONS.join(', ')}`);
      return;
    }

    let progressInterval: NodeJS.Timeout | null = null;

    try {
      setUploading(true);
      setError(null);
      setSuccess(null);
      setUploadProgress(0);

      // Simulate progress during upload with slower increments
      progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 95) return prev; // Stop at 95% until complete
          if (prev >= 70) return prev + 2; // Slow down after 70%
          return prev + 10;
        });
      }, 400); // Update every 400ms

      // Add timeout to prevent hanging forever
      const uploadPromise = uploadDocument(file, currentScope);
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Upload timeout - please try again')), 60000) // 60s timeout
      );

      await Promise.race([uploadPromise, timeoutPromise]);
      
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      
      setUploadProgress(100);
      setSuccess(`Successfully uploaded ${file.name}`);
      
      // Reload scopes and documents to update counts
      await loadScopes();
      await loadDocuments(currentScope);
      
      // Clear file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
      }
      console.error('Upload error:', err);
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploadProgress(0);
    } finally {
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      setUploading(false);
      setTimeout(() => setUploadProgress(0), 1000); // Reset after delay
    }
  };

  const handleDeleteScope = async () => {
    if (!scopeToDelete) return;

    try {
      setLoading(true);
      setError(null);
      await deleteScope(scopeToDelete);
      setSuccess(`Deleted all documents from scope '${scopeToDelete}'`);
      setDeleteDialogOpen(false);
      setScopeToDelete(null);
      await loadScopes();
      
      // Switch to first available scope
      if (scopeInfo && scopeInfo.scopes.length > 0) {
        const remainingScopes = scopeInfo.scopes.filter(s => s !== scopeToDelete);
        if (remainingScopes.length > 0) {
          setCurrentScope(remainingScopes[0]);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete scope');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      setSearching(true);
      setError(null);
      const results = await searchDocuments({
        query: searchQuery,
        scope: currentScope,
        k: 10,
        min_score: 0.3,
      });
      setSearchResults(results.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  const confirmDeleteScope = (scope: string) => {
    setScopeToDelete(scope);
    setDeleteDialogOpen(true);
  };

  const confirmDeleteDoc = (id: string, filename: string) => {
    setDocToDelete({ id, filename });
    setDeleteDocDialogOpen(true);
  };

  const handleDeleteDoc = async () => {
    if (!docToDelete) return;

    try {
      setLoading(true);
      setError(null);
      await deleteDocument(docToDelete.id);
      setSuccess(`Deleted ${docToDelete.filename}`);
      setDeleteDocDialogOpen(false);
      setDocToDelete(null);
      await loadScopes();
      await loadDocuments(currentScope);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    } finally {
      setLoading(false);
    }
  };

  const toggleFileSelection = (filename: string) => {
    setSelectedFiles(prev => {
      const newSet = new Set(prev);
      if (newSet.has(filename)) {
        newSet.delete(filename);
      } else {
        newSet.add(filename);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    const fileGroups = documents.reduce((acc, doc) => {
      const filename = doc.metadata.filename || 'Unknown';
      if (!acc[filename]) acc[filename] = [];
      acc[filename].push(doc);
      return acc;
    }, {} as Record<string, DocumentResponse[]>);

    const allFilenames = Object.keys(fileGroups);
    
    if (selectedFiles.size === allFilenames.length) {
      // Deselect all
      setSelectedFiles(new Set());
    } else {
      // Select all
      setSelectedFiles(new Set(allFilenames));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedFiles.size === 0) return;

    try {
      setLoading(true);
      setError(null);

      // Get all document IDs for selected files
      const fileGroups = documents.reduce((acc, doc) => {
        const filename = doc.metadata.filename || 'Unknown';
        if (!acc[filename]) acc[filename] = [];
        acc[filename].push(doc);
        return acc;
      }, {} as Record<string, DocumentResponse[]>);

      const docIdsToDelete: string[] = [];
      selectedFiles.forEach(filename => {
        const docs = fileGroups[filename] || [];
        docs.forEach(doc => docIdsToDelete.push(doc.id));
      });

      // Delete all selected documents
      await Promise.all(docIdsToDelete.map(id => deleteDocument(id)));

      setSuccess(`Deleted ${selectedFiles.size} ${selectedFiles.size === 1 ? 'file' : 'files'}`);
      setBulkDeleteDialogOpen(false);
      setSelectedFiles(new Set());
      await loadScopes();
      await loadDocuments(currentScope);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete documents');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background">
      <header className="border-b border-border/50 px-4 py-3 bg-background/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link href={`/${blueprint}`}>
              <Button variant="ghost" size="icon" className="hover:bg-primary/10">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div className="h-8 w-px bg-border" />
            <div>
              <h1 className="font-semibold text-lg capitalize flex items-center gap-2">
                <Database className="h-5 w-5 text-primary" />
                Knowledge Base
              </h1>
              <p className="text-xs text-muted-foreground">
                Manage documents for RAG-powered responses
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {scopeInfo && (
              <Badge variant="outline" className="font-mono">
                {scopeInfo.total_documents} documents
              </Badge>
            )}
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-auto">
        <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {success && (
            <Alert>
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertTitle>Success</AlertTitle>
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          {/* Upload Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload Documents
              </CardTitle>
              <CardDescription>
                Add files to the knowledge base for RAG-powered responses
              </CardDescription>
            </CardHeader>
              <CardContent className="space-y-4">
                <div
                  className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    dragActive
                      ? 'border-primary bg-primary/5'
                      : 'border-border hover:border-primary/50'
                  }`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    onChange={handleFileSelect}
                    className="hidden"
                    accept={SUPPORTED_EXTENSIONS.join(',')}
                    disabled={uploading}
                  />
                  <div className="flex flex-col items-center gap-2">
                    <FileText className="h-12 w-12 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium">
                        Drag and drop your file here, or{' '}
                        <button
                          onClick={() => fileInputRef.current?.click()}
                          className="text-primary hover:underline"
                          disabled={uploading}
                        >
                          browse
                        </button>
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Supports: {SUPPORTED_EXTENSIONS.join(', ')}
                      </p>
                    </div>
                  </div>
                </div>

                {uploading && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Uploading...</span>
                      <span className="font-medium">{uploadProgress}%</span>
                    </div>
                    <Progress value={uploadProgress} />
                  </div>
                )}

                <div className="text-xs text-muted-foreground space-y-1">
                  <p className="font-medium">Current scope: {currentScope}</p>
                  <p>Documents are organized by scope for better organization and retrieval.</p>
                </div>
              </CardContent>
            </Card>

          {/* Search Card - Full Width */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="h-5 w-5" />
                Semantic Search
              </CardTitle>
              <CardDescription>
                Find relevant documents using natural language queries
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Ask a question about your documents... (e.g., 'How do I deploy with Kubernetes?')"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  disabled={searching}
                  className="h-12 text-base"
                />
                <Button 
                  onClick={handleSearch} 
                  disabled={searching || !searchQuery.trim()}
                  size="lg"
                  className="px-8"
                >
                  {searching ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      Searching
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4 mr-2" />
                      Search
                    </>
                  )}
                </Button>
              </div>

              {searchResults.length > 0 && (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    Found {searchResults.length} relevant {searchResults.length === 1 ? 'result' : 'results'}
                  </p>
                  <div className="space-y-2 max-h-[400px] overflow-y-auto">
                    {searchResults.map((result, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <p className="text-sm font-medium flex items-center gap-2">
                            <File className="h-4 w-4" />
                            {result.metadata.filename || 'Document'}
                          </p>
                          <Badge variant="outline" className="text-xs">
                            {Math.round(result.score * 100)}% match
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground line-clamp-3">
                          {result.content}
                        </p>
                        <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                          <span>Scope: {result.scope}</span>
                          {result.metadata.file_type && (
                            <>
                              <span>•</span>
                              <span>{result.metadata.file_type}</span>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {searchQuery && searchResults.length === 0 && !searching && (
                <div className="text-center py-8">
                  <Search className="h-12 w-12 text-muted-foreground mx-auto mb-3 opacity-50" />
                  <p className="text-sm text-muted-foreground">
                    No results found for &quot;{searchQuery}&quot;
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Try different keywords or upload more documents
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Scopes Management */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FolderOpen className="h-5 w-5" />
                Document Scopes
              </CardTitle>
              <CardDescription>
                Organize documents by scope for better context retrieval
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading && !scopeInfo ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : scopeInfo && scopeInfo.scopes.length > 0 ? (
                <Tabs value={currentScope} onValueChange={setCurrentScope}>
                  <TabsList>
                    {scopeInfo.scopes.map((scope) => (
                      <TabsTrigger key={scope} value={scope}>
                        {scope} ({scopeInfo.counts[scope] || 0})
                      </TabsTrigger>
                    ))}
                  </TabsList>

                  {scopeInfo.scopes.map((scope) => (
                    <TabsContent key={scope} value={scope} className="space-y-4">
                      <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
                        <div>
                          <p className="font-medium">Scope: {scope}</p>
                          <p className="text-sm text-muted-foreground">
                            {scopeInfo.counts[scope] || 0} document chunks indexed
                          </p>
                        </div>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => confirmDeleteScope(scope)}
                          disabled={loading}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete Scope
                        </Button>
                      </div>

                      {/* Document List */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <h3 className="text-sm font-medium">Uploaded Documents</h3>
                          {documents.length > 0 && (
                            <div className="flex items-center gap-2">
                              {selectedFiles.size > 0 && (
                                <Button
                                  variant="destructive"
                                  size="sm"
                                  onClick={() => setBulkDeleteDialogOpen(true)}
                                  disabled={loading}
                                >
                                  <Trash2 className="h-4 w-4 mr-2" />
                                  Delete {selectedFiles.size} Selected
                                </Button>
                              )}
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={toggleSelectAll}
                                disabled={loading}
                              >
                                {selectedFiles.size === Object.keys(documents.reduce((acc, doc) => {
                                  const filename = doc.metadata.filename || 'Unknown';
                                  acc[filename] = true;
                                  return acc;
                                }, {} as Record<string, boolean>)).length ? (
                                  <>
                                    <X className="h-4 w-4 mr-2" />
                                    Deselect All
                                  </>
                                ) : (
                                  <>
                                    <CheckSquare className="h-4 w-4 mr-2" />
                                    Select All
                                  </>
                                )}
                              </Button>
                            </div>
                          )}
                        </div>
                        {loadingDocs ? (
                          <div className="flex items-center justify-center py-8">
                            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                          </div>
                        ) : documents.length > 0 ? (
                          <div className="space-y-2">
                            {/* Group documents by filename */}
                            {Object.entries(
                              documents.reduce((acc, doc) => {
                                const filename = doc.metadata.filename || 'Unknown';
                                if (!acc[filename]) {
                                  acc[filename] = [];
                                }
                                acc[filename].push(doc);
                                return acc;
                              }, {} as Record<string, DocumentResponse[]>)
                            ).map(([filename, docs]) => {
                              const isSelected = selectedFiles.has(filename);
                              
                              return (
                                <div
                                  key={filename}
                                  className={`p-3 rounded-lg border transition-all ${
                                    isSelected 
                                      ? 'bg-primary/5 border-primary/30 shadow-sm' 
                                      : 'bg-card hover:bg-accent/50'
                                  }`}
                                >
                                  <div className="flex items-start gap-3">
                                    <Checkbox
                                      checked={isSelected}
                                      onCheckedChange={() => toggleFileSelection(filename)}
                                      className="mt-1"
                                    />
                                    <div className="flex-1 min-w-0">
                                      <div className="flex items-center gap-2 mb-1">
                                        <FileText className="h-4 w-4 flex-shrink-0" />
                                        <p className="text-sm font-medium truncate">{filename}</p>
                                      </div>
                                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                                        <span>{docs.length} {docs.length === 1 ? 'chunk' : 'chunks'}</span>
                                        {docs[0].metadata.file_type && (
                                          <>
                                            <span>•</span>
                                            <span className="uppercase">{docs[0].metadata.file_type}</span>
                                          </>
                                        )}
                                        {docs[0].metadata.content_hash && (
                                          <>
                                            <span>•</span>
                                            <span className="font-mono">{docs[0].metadata.content_hash.substring(0, 8)}</span>
                                          </>
                                        )}
                                      </div>
                                      <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                                        {docs[0].content_preview}
                                      </p>
                                    </div>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => confirmDeleteDoc(docs[0].id, filename)}
                                      disabled={loading}
                                      className="flex-shrink-0"
                                    >
                                      <Trash2 className="h-4 w-4 text-destructive" />
                                    </Button>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          <div className="text-center py-8 border rounded-lg bg-muted/20">
                            <FileText className="h-12 w-12 text-muted-foreground mx-auto mb-3 opacity-50" />
                            <p className="text-sm text-muted-foreground">
                              No documents in this scope yet
                            </p>
                            <p className="text-xs text-muted-foreground mt-1">
                              Upload a file to get started
                            </p>
                          </div>
                        )}
                      </div>

                      <Alert>
                        <Database className="h-4 w-4" />
                        <AlertTitle>How it works</AlertTitle>
                        <AlertDescription>
                          When chatting with agents that have this scope configured, relevant
                          documents will automatically be retrieved and added to the context.
                        </AlertDescription>
                      </Alert>
                    </TabsContent>
                  ))}
                </Tabs>
              ) : (
                <div className="text-center py-8">
                  <Database className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground">
                    No documents yet. Upload your first document to get started!
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Scope Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Scope</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete all documents in scope &quot;{scopeToDelete}&quot;?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteScope} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Document Confirmation Dialog */}
      <Dialog open={deleteDocDialogOpen} onOpenChange={setDeleteDocDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{docToDelete?.filename}&quot;?
              This will remove all chunks of this document. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDocDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteDoc} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Delete Confirmation Dialog */}
      <Dialog open={bulkDeleteDialogOpen} onOpenChange={setBulkDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Selected Documents</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {selectedFiles.size} selected {selectedFiles.size === 1 ? 'file' : 'files'}?
              This will remove all chunks of these documents. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-[200px] overflow-y-auto">
            <ul className="text-sm space-y-1">
              {Array.from(selectedFiles).map(filename => (
                <li key={filename} className="flex items-center gap-2">
                  <FileText className="h-3 w-3" />
                  {filename}
                </li>
              ))}
            </ul>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBulkDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleBulkDelete} disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Delete {selectedFiles.size} {selectedFiles.size === 1 ? 'File' : 'Files'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
