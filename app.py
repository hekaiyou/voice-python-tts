import os
import io
import json
import uuid
import bson.binary
from flask import Flask, request, Response
from rainbond_python.db_connect import DBConnect
from rainbond_python.parameter import Parameter
from utils.to_speech import ToSpeech

app = Flask(__name__)
db = DBConnect(db='dragonli', collection='speechs')

app.config['SEPPCH_DIR'] = 'speechs/'


@app.route('/api/1.0/tts', methods=['GET'])
def api_tts():
    parameter = Parameter(request)

    if parameter.method == 'GET':
        param = parameter.verification(checking=parameter.param_url, verify={
                                       'text': str, 'language': str}, optional={'language': 'auto'})
        # 根据文档是否存在
        if db.does_it_exist(docu={'text': param['text'], 'language': param['language']}):
            documen = db.mongo_collection.find_one(
                {'text': param['text'], 'language': param['language']})
            # 返回.wav音频
            return Response(documen['wav'], mimetype="audio/x-wav")
        else:
            tts = ToSpeech()
            # TTS操作
            stream = tts.recognize(
                text=param['text'], language=param['language'])
            # 文件保存操作
            wav_path = os.path.join(
                app.config['SEPPCH_DIR'], str(uuid.uuid4()) + '.wav'
            )
            # 判断TTS是否成功
            if not stream.can_read_data(requested_bytes=1):
                return '文本转语音失败', 500, []
            # 保存文件到服务指定目录
            stream.save_to_wav_file(wav_path)
            # 文件写入Mongo数据库
            with open(wav_path, 'rb') as f_wav:
                content = io.BytesIO(f_wav.read())
                insert_dict = {
                    'text': param['text'],
                    'language': param['language'],
                    'wav': bson.binary.Binary(content.getvalue())
                }
            # 删除文件
            os.remove(wav_path)
            result = db.write_one_docu(docu=insert_dict)
            if result:
                return Response(insert_dict['wav'], mimetype="audio/x-wav")
            else:
                return '语音合成文件无法被保存', 500, []


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
