import torch
import torch.nn as nn
import torch.nn.functional as F

from transformer.Models import Encoder, Decoder
from transformer.Layers import PostNet
from modules import VarianceAdaptor, EmbeddingIntegrator, ProsodyEncoder
from utils import get_mask_from_lengths
import hparams as hp

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


class FastSpeech2(nn.Module):
    """ FastSpeech2 """

    def __init__(self, use_postnet=True, num_speakers=1):
        super(FastSpeech2, self).__init__()

        self.multi_speaker = hp.multi_speaker
        self.encode_prosody = hp.encode_prosody
        if self.multi_speaker:
            # Initialize the speaker embeddings
            self.embed_speakers = nn.Embedding(num_speakers, hp.speaker_embed_dim)
            self.embed_speakers.weight.data.normal_(0, hp.speaker_embed_weight_std)
            self.speaker_integrator = EmbeddingIntegrator()
        if self.encode_prosody:
            self.prosody_encoder = ProsodyEncoder()
            self.prosody_integrator = EmbeddingIntegrator()

        self.encoder = Encoder()
        self.variance_adaptor = VarianceAdaptor()

        self.decoder = Decoder()
        self.mel_linear = nn.Linear(
            hp.decoder_hidden + hp.speaker_embed_dim + hp.prosody_embed_dim,
            hp.n_mel_channels)

        self.use_postnet = use_postnet
        if self.use_postnet:
            self.postnet = PostNet()

    def forward(
        self,
        src_seq,
        src_len,
        mel_tgt=None,
        mel_len=None,
        d_target=None,
        p_target=None,
        e_target=None,
        max_src_len=None,
        max_mel_len=None,
        speaker_ids=None,
        d_control=1.0,
        p_control=1.0,
        e_control=1.0
    ):
        src_mask = get_mask_from_lengths(src_len, max_src_len)
        mel_mask = get_mask_from_lengths(
            mel_len, max_mel_len) if mel_len is not None else None

        encoder_output = self.encoder(src_seq, src_mask)
        if self.multi_speaker and speaker_ids is not None:
            speaker_embeddings = self.embed_speakers(speaker_ids)
            encoder_output = self.speaker_integrator(encoder_output, speaker_embeddings)
        if self.encode_prosody and mel_tgt is not None:
            prosody_embeddings = self.prosody_encoder(mel_tgt, mel_mask)
            encoder_output = self.prosody_integrator(encoder_output, prosody_embeddings)

        if d_target is not None:
            variance_adaptor_output, d_prediction, p_prediction, e_prediction, _, _ = self.variance_adaptor(
                encoder_output, src_mask, mel_mask, d_target, p_target, e_target, max_mel_len, d_control, p_control, e_control)
        else:
            variance_adaptor_output, d_prediction, p_prediction, e_prediction, mel_len, mel_mask = self.variance_adaptor(
                encoder_output, src_mask, mel_mask, d_target, p_target, e_target, max_mel_len, d_control, p_control, e_control)


        decoder_output = self.decoder(variance_adaptor_output, mel_mask)
        mel_output = self.mel_linear(decoder_output)

        if self.use_postnet:
            mel_output_postnet = self.postnet(mel_output) + mel_output
        else:
            mel_output_postnet = mel_output

        return mel_output, mel_output_postnet, d_prediction, p_prediction, e_prediction, src_mask, mel_mask, mel_len


if __name__ == "__main__":
    # Test
    model = FastSpeech2(use_postnet=False)
    print("Model:")
    print(model)
    print(sum(param.numel() for param in model.parameters()))
