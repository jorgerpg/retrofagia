export type RecordItem = {
  id: string;
  matrix_code: string;
  title: string;
  artist: string;
  year?: number;
  genre?: string;
  label?: string;
  cover_url?: string;
};


export type CollectionItem = {
  record: RecordItem;
  is_favorite?: boolean;
  added_at?: string;
  condition?: "Mint" | "Near Mint" | "Very Good+" | "Good" | "Fair";
};

export type NewRecordForm = {
  matrix_code: string;
  title: string;
  artist: string;
  year?: number;
  genre?: string;
  label?: string;
};

export type CommentItem = {
  id: string;
  user_id: string;
  record_id: string;
  content: string;
  created_at: string;
};

export type MyReview = {
  id: string;
  user_id: string;
  record_id: string;
  rating: number;           // 0..5
  comment?: string | null;
  created_at: string;
};