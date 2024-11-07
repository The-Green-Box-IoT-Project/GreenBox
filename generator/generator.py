import uuid


def generate_id(prefix):
    out_id = '%s_%s' % (prefix, uuid.uuid4())
    return out_id


if __name__ == '__main__':
    new_id = generate_id('dht11')
    print(f'Generated id: {new_id}')
