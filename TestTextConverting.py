# -*- coding: utf-8 -*-
import re
from bs4 import BeautifulSoup


text = """
<style type="text/css">saasdgsgddsgsf</style>(img1)
Двигайте слайдер, чтобы изменить прозрачность.
"""


def send_object_text(text):
    tags_list = ['font', 'p', 'div', 'span', 'td', 'tr', 'th', 'table', 'hr', 'object', 'param', 'audio', 'source',
                 'embed', 'link', 'iframe', 'address', 'body', 'html', 'li', 'ol', 'details', 'ul', 'script', 'video',
                 'b', 'center', 'u', 'i', 'strong', 'em', 'style', 'script']

    if 'table' in text or 'script' in text or 'object' in text or 'audio' in text:
        text = 'В тексте найдены и вырезаны скрипты таблицы, аудию и/или иные объекты\r\n' \
               '\xE2\x9D\x97<b>Информация в чате может отличаться от движка</b>\xE2\x9D\x97\r\n' + text

    text = cut_script(text)
    text, images = cut_images(text)
    text = cut_formatting(text, tags_list)
    text = reformat_links(text)
    text, indexes = handle_coords(text)
    while '\r\n\r\n\r\n' in text:
        text = text.replace('\r\n\r\n\r\n', '\r\n\r\n')
    text = cut_extra_links_endings(text)

    return text, images, indexes


def cut_formatting(text, tags_list):
    text = text.replace('&amp;', '&')

    br_tags_to_cut = ['</br>', '</br >', '</ br>', '<br/>', '<br />', '<br>', '&nbsp;']
    for br_tag in br_tags_to_cut:
        text = text.replace(br_tag, '\r\n')

    text = cut_style(text)
    for tag in tags_list:
        text = cut_tag(text, tag)

    h_tags = re.findall(r'<h\d>', text)
    soup = BeautifulSoup(text)
    for h_tag in h_tags:
        for h in soup.find_all('h%s' % h_tag[-2]):
            text = text.replace(str(h), h.text.encode('utf-8'))

    return text


def cut_images(text):
    images = list()
    for i, img in enumerate(re.findall(r'<img[^>]*>|<image[^>]*>', text)):
        soup = BeautifulSoup(img)
        img_soup = soup.find_all('img') if 'img' in img else soup.find_all('image')
        images.append(img_soup[0].get('src').encode('utf-8'))
        image = '(img%s)' % str(i+1)
        text = text.replace(img, image)
    text = text.replace('<img>', '')
    text = text.replace('</img>', '')

    return text, images


def handle_coords(text):
    indexes = list()
    locations = dict()

    soup = BeautifulSoup(text)
    for ahref in soup.find_all('a'):
        coord_links = find_coords(ahref.text.encode('utf-8'))
        if coord_links:
            str_ahref = str(ahref)
            str_ahref = str_ahref.replace('&amp;', '&')
            text = text.replace(str_ahref, ahref.text.encode('utf-8'))

    links = re.findall(r'<a[^>]+>', text)
    for i, link in enumerate(links):
        coords = find_coords(link)
        if coords:
            replacement = '(link%s)' % i
            text = text.replace(link, replacement)

    coords = list()
    init_coords = find_coords(text)
    for coord in init_coords:
        if coord in coords:
            continue
        coords.append(coord)
    if coords:
        for coord in coords:
            i = 1 if not locations else len(locations.keys()) + 1
            coord_Y_G = make_Y_G_links(coord) + ' - <b>' + str(i) + '</b>'
            text = text.replace(coord, coord_Y_G)
            if unicode(i) not in locations.keys():
                indexes.append(i)
            locations[str(i)] = coord

    for rep in re.findall(r'\(link\d+\)', text):
        j = re.findall(r'\d+', rep)
        text = text.replace(rep, links[int(j[0])])

    return text, indexes


def make_Y_G_links(coord):
    lat = re.findall(r'\d\d\.\d{4,7}', coord)[0]
    long = re.findall(r'\d\d\.\d{4,7}', coord)[1]
    Y = '<a href="http://maps.yandex.ru/?text=%s,%s">[Y]</a>' % (lat, long)
    G = '<a href="https://maps.google.com/?daddr=%s,%s&t=m">[G]</a>' % (lat, long)
    # G = '<a href="https://www.google.com/maps/place/%s,%s">[G]</a>' % (lat, long)
    coord_Y_G = '<b>' + coord + '</b> ' + Y + ' ' + G
    return coord_Y_G


def reformat_links(text):
    links_to_lower = re.findall(r'<A\sH[^>]+>|'
                                r'<A\sh[^>]+>', text)
    for link in links_to_lower:
        soup = BeautifulSoup(link)
        for a in soup.find_all('a'):
            link_lower = link.replace(a.get('href').encode('utf-8'), 'link')
            link_lower = link_lower.lower()
            link_lower = link_lower.replace('link', a.get('href').encode('utf-8'))
            text = text.replace(link, link_lower)
    text = text.replace('</A>', '</a>')
    text = text.replace('<A/>', '<a/>')
    text = text.replace('<a/>', '</a>')

    links_to_check = re.findall(r'<a[^>]+>', text)
    for link in links_to_check:

        href = re.search(r'href\s*=\s*[^>\s]+', link).group(0)
        if '"' not in href:
            soup = BeautifulSoup(link)
            for a in soup.find_all('a'):
                text = text.replace(href, 'href="' + a.get('href').encode('utf-8') + '"')
    return text


def cut_extra_links_endings(text):
    a_opens = re.findall(r'<a[^>]+>', text)
    a_closings = re.findall(r'</a>', text)
    if len(a_closings) > len(a_opens):
        links = re.findall(r'<a\sh.+>.*</a>', text)
        for i, link in enumerate(links):
            cut_link = '(link%s)' % i
            text = text.replace(link, cut_link)
        text = text.replace('</a>', '')
        for i, link in enumerate(links):
            cut_link = '(link%s)' % i
            text = text.replace(cut_link, link)
    return text


def cut_links_change_small_symbol(text):
    links = list()
    links_indexes = list()
    links_text = list()

    str_ahrefs = re.findall(r'<a\sh.+>.*</a>', text)
    for i, str_ahref in enumerate(str_ahrefs):
        link = '(link%s)' % i
        soup = BeautifulSoup(str_ahref)
        ahref = soup.find_all('a')[0]
        links.append(ahref.get('href').encode('utf-8'))
        str_ahref = str_ahref.replace('&amp;', '&')
        text = text.replace(str_ahref, ahref.text.encode('utf-8') + link)
        links_text.append(str_ahref)
        links_indexes.append(ahref.text.encode('utf-8') + link)
    text_cut_links = text
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    for i, link_index in enumerate(links_indexes):
        text = text.replace(link_index, links_text[i])
    return text, links, text_cut_links


def cut_tag(text, tag):
    tag_reps = re.findall(r'<%s[^>]*>|<%s[^>]*>' % (tag, tag.upper()), text)
    for tag_rep in tag_reps:
        text = text.replace(tag_rep, '')
    text = text.replace('</%s>' % tag, '')
    text = text.replace('</%s>' % tag.upper(), '')

    return text


def cut_style(text):
    soup = BeautifulSoup(text)
    for rep in soup.find_all('style'):
        string = str(rep.string)
        text = text.replace(string, '')

    style_rests = ['<style>', '<style >', '<style/>', '<style />', '<style"">', '</style>', '<style  />']
    for style_rest in style_rests:
        for st in re.findall(style_rest, text):
            text = text.replace(st, '')

    return text


def cut_script(text):
    soup = BeautifulSoup(text)
    for script in soup.find_all('script'):
        text = text.replace(str(script), '')

    return text


def find_coords(text):
    coords = re.findall(r'\d\d\.\d{4,7},\s{,3}\d\d\.\d{4,7}|'
                        r'\d\d\.\d{4,7}\s{1,3}\d\d\.\d{4,7}|'
                        r'\d\d\.\d{4,7}\r\n\d\d\.\d{4,7}|'
                        r'\d\d\.\d{4,7},\r\n\d\d\.\d{4,7}', text)
    return coords


text, images, indexes = send_object_text(text)
print text