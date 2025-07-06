from flask import Flask, jsonify, request  
from googleapiclient.discovery import build
from flask_cors import CORS # Importe CORS para permitir requisições do seu frontend
import os

app = Flask(__name__)
CORS(app) # Habilita CORS para todas as rotas, permitindo que seu frontend no Vercel acesse

# --- SUA CHAVE DE API DO YOUTUBE VAI AQUI ---
YOUTUBE_API_KEY = 'AIzaSyCGAe8troY2GlZ2LjirWNjuKzXY8DbZcKk'
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YOUTUBE_API_KEY)

# Função auxiliar para formatar números grandes (K, M, B)
def format_large_number(num):
    num = float(num)
    if num >= 1_000_000_000:
        return f'{num / 1_000_000_000:.1f}B'
    if num >= 1_000_000:
        return f'{num / 1_000_000:.1f}M'
    if num >= 1_000:
        return f'{num / 1_000:.1f}K'
    return str(int(num))

@app.route('/trending_videos', methods=['GET'])
def get_trending_videos():
    try:
        # Define o ID da região para o Brasil (BR)
        region_code = request.args.get('regionCode', 'BR') # Pega da URL, padrão BR
        
        # Parâmetros de busca da API (inicialmente apenas por termo de busca ou em alta)
        search_query = request.args.get('q', '') # Termo de busca (se existir)
        category_id = request.args.get('categoryId', '') # ID da categoria (se existir)

        if search_query:
            # Se houver um termo de busca, usa o endpoint 'search'
            search_response = Youtube().list(
                q=search_query,
                part="snippet",
                type="video",
                regionCode=region_code,
                maxResults=20
            ).execute()
            
            video_ids = [item['id']['videoId'] for item in search_response.get('items', []) if 'videoId' in item['id']]
            
            if not video_ids:
                return jsonify([]) # Retorna vazio se não encontrar vídeos com a busca

            # Agora, busca detalhes estatísticos para esses vídeos
            videos_request = youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=','.join(video_ids) # Busca múltiplos IDs de vídeo
            )
            response = videos_request.execute()

        else:
            # Se não houver termo de busca, busca vídeos em alta
            request_youtube = youtube.videos().list(
                part="snippet,contentDetails,statistics",
                chart="mostPopular",
                regionCode=region_code,
                maxResults=20
            )
            response = request_youtube.execute()

        videos_data = []
        for item in response.get('items', []):
            # Garante que o item possui 'snippet' e 'statistics'
            if 'snippet' not in item or 'statistics' not in item:
                continue

            title = item['snippet']['title']
            channel_name = item['snippet']['channelTitle']
            video_id = item['id'] if isinstance(item['id'], str) else item['id'].get('videoId') # Lida com diferentes estruturas de ID
            video_url = f"https://www.youtube.com/watch?v={video_id}" # URL correta para o YouTube
            thumbnail_url = item['snippet']['thumbnails']['high']['url'] # Miniatura de alta qualidade

            view_count = int(item['statistics'].get('viewCount', 0))
            like_count = int(item['statistics'].get('likeCount', 0))
            comment_count = int(item['statistics'].get('commentCount', 0))

            # Calcular engajamento (exemplo simples: likes + comments / views)
            engagement_score = 0
            if view_count > 0:
                engagement_score = ((like_count + comment_count) / view_count) * 100

            videos_data.append({
                'title': title,
                'channelName': channel_name,
                'videoId': video_id,
                'videoUrl': video_url,
                'thumbnailUrl': thumbnail_url,
                'viewCountRaw': view_count,
                'viewCountFormatted': format_large_number(view_count),
                'likeCount': like_count,
                'commentCount': comment_count,
                'engagementScore': f'{engagement_score:.2f}%'
            })
        
        return jsonify(videos_data)

    except Exception as e:
        print(f"Erro ao buscar vídeos: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)