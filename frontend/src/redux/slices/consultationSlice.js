// src/redux/slices/consultationSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';

const initialState = {
  consultationId: null,
  userDetails: null,
  chatHistory: [],
  diagnosis: null,
  loading: false,
  error: null
};

export const startConsultation = createAsyncThunk(
  'consultation/start',
  async (userData, { rejectWithValue }) => {
    try {
      const response = await axios.post('http://localhost:8000/api/consultation/start', userData);
      console.log('API Response in slice:', response.data);
      return response.data;
    } catch (err) {
      console.error('Error in startConsultation:', err);
      return rejectWithValue(err.response?.data?.detail || 'Failed to start consultation');
    }
  }
);

const consultationSlice = createSlice({
  name: 'consultation',
  initialState,
  reducers: {
    addChatMessage: (state, action) => {
      state.chatHistory.push(action.payload);
    },
    setDiagnosis: (state, action) => {
      state.diagnosis = action.payload;
    },
    clearConsultation: (state) => {
      return initialState;
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(startConsultation.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(startConsultation.fulfilled, (state, action) => {
        console.log('Fulfilled payload:', action.payload);
        state.loading = false;
        state.consultationId = action.payload.consultationId;
        state.userDetails = action.payload.userDetails;
      })
      .addCase(startConsultation.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || action.error.message;
      });
  }
});

export const { addChatMessage, setDiagnosis, clearConsultation } = consultationSlice.actions;
export default consultationSlice.reducer;