import nltk
class ListingSummarizer:
    def extractive_summary(self, remarks, entities, num_sentences=2):
        sentences = nltk.sent_tokenize(remarks)
        # Score sentences by entity mentions and position
        scores = []
        for i, sent in enumerate(sentences):
            score = 0
            # First sentence bonus
            if i == 0:
                score += 2
            # Entity mentions
            if str(entities.get('bedrooms', '')) in sent:
                score += 1
            if 'pool' in sent.lower():
                score += 1
            scores.append((score, sent))
        # Return top sentences
        top_sentences = sorted(scores, reverse=True)[:num_sentences]
        return ' '.join(s[1] for s in sorted(top_sentences, key=lambda x: sentences.index(x[1])))