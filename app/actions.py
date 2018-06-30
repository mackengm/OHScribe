from flask import flash, redirect, url_for
from app import app
import os
import io
import sys
import re
from lxml import etree

# Internal / support functions go here.
# -------------------------------------------------------------------------


def upload_to_server(file):
  flash("upload_to_server called with file '{}'.  Returning True".format(file), 'info')
  return True


def checkfile(filename):
  if '/' in filename:
    filepath = filename
  else:
    filepath = "{0}/{1}".format(app.config['UPLOAD_FOLDER'], filename)
  return filepath


def sanitize_xml(line):
  line = line.replace('&lt;', '<').replace('&gt;', '>').replace(' & ', ' &amp; ').replace('<speaker>', '\n    <speaker>').strip('\n')
  if len(line) > 0:                                                                   # don't return any empty lines!
    return "{}\n".format(line)
  else:
    return False


# Transform any XML with a XSLT
# Lifted from https://gist.github.com/revolunet/1154906

def xsl_transformation(xmlfile, xslfile="./ohscribe.xsl"):
  
  try:
    with open(xslfile, 'r') as xsl:
      xslt = xsl.read( )
      root = etree.XML(xslt)
      transform = etree.XSLT(root)
      xml = xmlfile.read( )
      f = io.StringIO(xml)
      doc = etree.parse(f)
      result = transform(doc)

  except:
    msg = "Unexpected error: {}".format(sys.exc_info()[0])
    flash(msg, 'error')
    return redirect(url_for('main'))
  
  return result


# Return a new file name with '-insert' added before the .ext
# IOH now treats an underscore here as indication of a language, like _english, so change any/all underscores to dashes!

def make_new_filename(input_file_name, insert):
  input_file_name.replace("_", "-")
  name, ext = os.path.splitext(input_file_name)
  return "{name}-{insert}{ext}".format(name=name, insert=insert, ext=ext)



# Actions here.
# ------------------------------------------------------------


# Cleanup the XML

def do_cleanup(filename):
  filepath = checkfile(filename)
  clean = make_new_filename(filepath, 'clean')

  try:
    with open(filepath, 'r') as xmlfile, open(clean, 'w+') as cleanfile:
      if xmlfile.name.rsplit(".")[-1] != "xml":
        msg = "File name should have a .xml extension!"
        flash(msg, 'warning')

      counter = 0
      for line in xmlfile:
        cleaned = sanitize_xml(line)
        if cleaned:
          cleanfile.write(cleaned)
          counter += 1

    with open(clean, 'r') as cleanfile:
      msg = "Clean-up is complete. {0} lines of '{1}' were processed to create '{2}'.".format(counter, filename, clean)
      flash(msg, 'info')
      detail = " ".join(cleanfile.readlines( )[0:10])
      guidance = "Please engage the 'Transform' feature to change '{}' into proper IOH XML format.".format(clean)

    return clean, msg, detail, guidance

  except:
    msg = "Unexpected error: {}".format(sys.exc_info()[0])
    flash(msg, 'error')
    return redirect(url_for('main'))


# Transform XML from InqScribe to IOH

def do_transform(filename):
  filepath = checkfile(filename)

  try:
    with open(filepath, 'r+') as xmlfile:

      # Now transform it
      IOH_xml = xsl_transformation(xmlfile)
      if IOH_xml is None:
        msg = "Error transforming file `{}'.".format(xmlfile)
        flash(msg, 'error')
        return msg

      ioh = make_new_filename(filepath, 'IOH')

      ioh_file = open(ioh, "w")
      ioh_file.write(str(IOH_xml))
      ioh_file.close()
      msg = "XML transformation output is in {}".format(ioh)
      flash(msg, 'info')

    with open(ioh, 'r') as transfile:
      msg = "XSLT transformation is complete and the results are in '{}'.".format(ioh)
      detail = " ".join(transfile.readlines( )[0:10])
      guidance = "Click the 'Proceed' button below to convert hh:mm:ss times to seconds."

    return ioh, msg, detail, guidance

  except:
    msg = "Unexpected error: {}".format(sys.exc_info()[0])
    flash(msg, 'error')
    return redirect(url_for('main'))


# Convert hh:mm:ss times to seconds

def do_hms_conversion(filename):
  filepath = checkfile(filename)
  secname = make_new_filename(filepath, 'sec')

  try:
    with open(filepath, 'r') as xmlfile, open(secname, 'w') as secfile:
      counter = 0
      
      for line in xmlfile:
        matched = re.match(r'(.*)(\d\d:\d\d:\d\d\.\d\d)(.*)', line)
        if matched:
          hms = matched.group(2)
          h, m, s = hms.split(':')
          sec = str(int(h) * 3600 + int(m) * 60 + float(s))
          line = line.replace(hms, sec)
          counter += 1
        secfile.write(line)

      msg = "hh:mm:ss conversion output is in {0} with {1} modified lines".format(secname, counter)
      flash(msg, 'info')

    with open(secname, 'r') as secfile:
      msg = "Conversion of hh:mm:ss times to seconds is complete.  Results are in '{}'.".format(secname)
      detail = " ".join(secfile.readlines()[0:10])
      guidance = "Consider using the 'Format Speaker Tags' action to properly format speaker names in '{}'.".format(
        secname)

    return secname, msg, detail, guidance

  except:
    msg = "Unexpected error: {}".format(sys.exc_info()[0])
    flash(msg, 'error')
    return redirect(url_for('main'))


# Format <speaker> tags

def do_speaker_tags(filename):
  filepath = checkfile(filename)
  final = make_new_filename(filepath, 'final')
  
  try:
    with open(filepath, 'r') as xmlfile, open(final, 'wb') as finalfile:

      # Identify all <speaker> tags
    
      q = etree.parse(xmlfile)
      
      speaker_tags = q.findall('.//speaker')
      speakers = dict()
      num = 1

      for tag in speaker_tags:
        if tag.text:
          full = tag.text.strip()
          first, rest = full.split(' ', 1)
          first = first.strip()
          if first not in speakers:
            speakers[first] = {'number': num, 'class': "<span class='oh_speaker_" + str(num) + "'>", 'full_name': full}
            num += 1

      # Examine each <cue>. Identify speakers in the transcript.text and modify that text accordingly
        
      cue_tags = q.findall('.//cue')
      
      for tag in cue_tags:
        t = tag.find('transcript')
        text = t.text.replace('\n', ' ').replace('  ', ' ').replace(' :', ':').replace(' |', '|')

        words = text.split()
        t.text = ''
        count = 0
        speakers_found = []

        for word in words:
          if word.endswith('|'):
            speaker = word.strip('|')

            if speaker in speakers:
              if count > 0:
                t.text += '</span></span>'
              t.text += speakers[speaker]['class'] + speaker + ": " + "<span class='oh_speaker_text'>"

              if speaker not in speakers_found:
                speakers_found.append(speaker)
              count += 1
              
            else:
              msg = "Referenced speaker '{}' has no corresponding <speaker> tag!".format(speaker)
              flash(msg, 'error')
              return redirect(url_for('main'))

          else:
            t.text += " " + word
  
        t.text += '</span></span>'

        # Now build a proper <speaker> tag from the references found, and apply it
        
        if speaker not in speakers_found:
          msg = "Speaker '{}' was found in a <cue> with NO correspinding <speaker> tag!".format(speaker)
          flash(msg, 'error')
          return redirect(url_for('main'))

        speaker_tag = ''
        for speaker in speakers_found:
          speaker_tag += speakers[speaker]['full_name'] + ' & '
        speaker_tag = speaker_tag.strip(' & ')

        t = tag.find('speaker')
        t.text = speaker_tag

      finalfile.write(etree.tostring(q, pretty_print=True))

    with open(final, 'r') as finalfile:
      msg = "Speaker formatting in transcript '{}' is complete.".format(final)
      flash(msg, 'info')
      detail = " ".join(finalfile.readlines()[0:20])
      guidance = "Consider performing an analysis of '{}' to flag <cues> that are potentially too long.".format(final)

    return final, msg, detail, guidance

  except:
    msg = "Unexpected error: {}".format(sys.exc_info()[0])
    flash(msg, 'error')
    return redirect(url_for('main'))


# Analyze and report <cue> lengths

def do_analyze(filename):
  filepath = checkfile(filename)

  try:
    with open(filepath, 'r+') as xmlfile:

      problem_cues = "Long cue start times: "
      problems = 0
      q = etree.parse(xmlfile)
      cue_tags = q.findall('.//cue')
      cue_num = 0

      for tag in cue_tags:
        t = tag.find('start')
        start = int(float(t.text))
        m, s = divmod(start, 60)
        cue_start = '{:d}:{:02d} '.format(m, s)

        t = tag.find('transcript')
        text = t.text.replace('\n', ' ').replace('  ', ' ').replace(' :', ':').replace(' |', '|')

        words = text.split()
        cue_lines = 0
        cue_chars = 0
        assumed_line_max = 80    # assuming 80 characters per line for a max target

        for word in words:
          if word.endswith('>'):  # ignore all tags
            continue
          if word.startswith('<'):  # ignore all tags
            continue

          if word.endswith(':'):  # found a new speaker, new line
            cue_lines += 1
            cue_chars = len(word) - 20  # accounts for the class='oh_speaker_x'> tag

          else:
            cue_chars += len(word) + 1
            if cue_chars > assumed_line_max:
              cue_lines += 1
              cue_chars = 0

        # Done with cue text analysis... report if necessary

        if cue_lines == 0:
          msg = "Cue `{}' is EMPTY. Remove that cue before proceeding!".format(cue_num)
          flash(msg, 'error')
          return redirect(url_for('main'))

        if cue_lines > 10:
          problem_cues += str(cue_start)
          problems += 1
        cue_num += 1

      # Analysis is complete.  Report
      
      if problems > 0:
        msg = "One or more long cues were found in '{}'".format(filename)
        flash(msg, 'warning')
        guidance = "Please visit the transcript XML and consider dividing these cues into smaller sections."
        return filepath, msg, problem_cues, guidance

      if problems == 0:
        msg = "Analysis is complete and there were NO problems found in transcript `{}'.".format(filename)
        flash(msg, 'info')

    return filepath, msg, "", ""

  except:
    msg = "Unexpected error: {}".format(sys.exc_info()[0])
    flash(msg, 'error')
    return redirect(url_for('main'))


# Do all of the above, in sequence.

def do_all(filename):
  filepath = checkfile(filename)
  clean, msg, details, guidance = do_cleanup(filepath)
  xformed, msg, details, guidance = do_transform(clean)
  times, msg, details, guidance = do_hms_conversion(xformed)
  final, msg, details, guidance = do_speaker_tags(times)
  analyzed, msg, details, guidance = do_analyze(final)
  return analyzed, msg, details, guidance


  #
  # def button_analyze_callback():
  #   """ what to do when the "Analyze" button is pressed """
  #
  #   xmlfile = entry.get()
  #
  #   if xmlfile.rsplit(".")[-1] != "xml":
  #     statusText.set("Filename must have a .xml extension!")
  #     message.configure(fg="red")
  #     return
  #
  #   else:
  #     """ examine each cue, count number of lines of text and report any longer than 10 lines """
  #     problem_cues = "Long cue start times: "
  #     problems = 0
  #     q = etree.parse(xmlfile)
  #     cue_tags = q.findall('.//cue')
  #     cue_num = 0
  #
  #     for tag in cue_tags:
  #       t = tag.find('start')
  #       start = int(float(t.text))
  #       m, s = divmod(start, 60)
  #       cue_start = '{:d}:{:02d} '.format(m, s)
  #
  #       t = tag.find('transcript')
  #       text = t.text.replace('\n', ' ').replace('  ', ' ').replace(' :', ':').replace(' |', '|')
  #
  #       words = text.split()
  #       cue_lines = 0
  #       cue_chars = 0
  #       assumed_line_max = 80  # assuming 80 characters per line for a max target
  #
  #       for word in words:
  #         if word.endswith('>'):  # ignore all tags
  #           continue
  #         if word.startswith('<'):  # ignore all tags
  #           continue
  #
  #         if word.endswith(':'):  # found a new speaker, new line
  #           cue_lines += 1
  #           cue_chars = len(word) - 20  # accounts for the class='oh_speaker_x'> tag
  #
  #         else:
  #           cue_chars += len(word) + 1
  #           if cue_chars > assumed_line_max:
  #             cue_lines += 1
  #             cue_chars = 0
  #
  #       """ done with cue text analysis...report if necessary """
  #       if cue_lines == 0:
  #         statusText.set("Cue `{}' is EMPTY. Remove it before proceeding!".format(cue_num))
  #         message.configure(fg="red")
  #         return
  #       if cue_lines > 10:
  #         problem_cues += str(cue_start)
  #         problems += 1
  #       cue_num += 1
  #
  #     """ analysis is complete.  report """
  #     if problems == 0:
  #       statusText.set("Analysis is complete, no problems found in transcript `{}'.".format(xmlfile))
  #       message.configure(fg="dark green")
  #       return
  #
  #     if problems > 0:
  #       statusText.set(problem_cues)
  #       message.configure(fg="red")
  #       return
  #
  # def button_reformat_callback():
  #   """ what to do when the "Reformat" button is pressed """
  #
  #   xmlfile = entry.get()
  #   if xmlfile.rsplit(".")[-1] != "xml":
  #     statusText.set("Filename must have a .xml extension!")
  #     message.configure(fg="red")
  #     return
  #
  #   IOH_xmlfile = get_IOH_filename(xmlfile)
  #   copyfile(xmlfile, IOH_xmlfile)
  #
  #   """ make it pretty """
  #   parser = etree.XMLParser(resolve_entities=False, strip_cdata=False)
  #   document = etree.parse(IOH_xmlfile, parser)
  #   document.write(IOH_xmlfile, pretty_print=True, encoding='utf-8')
  #
  #   """ identify all the speaker tags """
  #   q = etree.parse(IOH_xmlfile)
  #   speaker_tags = q.findall('.//speaker')
  #   speakers = dict()
  #   num = 1
  #
  #   for tag in speaker_tags:
  #     if tag.text:
  #       full = tag.text.strip()
  #       if ' ' not in full:
  #         first = full
  #       else:
  #         first, rest = full.split(' ', 1)
  #
  #       first = first.strip()
  #       if first not in speakers:
  #         speakers[first] = {'number': num, 'class': "<span class='oh_speaker_" + str(num) + "'>", 'full_name': full}
  #         num += 1
  #
  #   """ examine each cue, identify THE speaker and modify the cue accordingly """
  #   cue_tags = q.findall('.//cue')
  #   speakers_found = []
  #
  #   for tag in cue_tags:
  #     s = tag.find('speaker')
  #     if ' ' not in s.text.strip():
  #       first = s.text.strip()
  #     else:
  #       first, rest = s.text.strip().split(' ', 1)
  #     first = first.strip()
  #     if first not in speakers_found:
  #       speakers_found.append(first)
  #     t = tag.find('transcript')
  #     if t.text is None:
  #       statusText.set("Transcript has no text at source line " + str(t.sourceline) + "!")
  #       message.configure(fg="red")
  #       return
  #
  #     text = t.text.replace('\n', ' ').replace('  ', ' ').replace(' :', ':').replace(' |', '|')
  #     t.text = ''
  #     try:
  #       t.text += speakers[first]['class'] + first + ": " + "<span class='oh_speaker_text'>" + text + '</span></span>'
  #     except KeyError:
  #       statusText.set("Transcript 'KeyError' at source line " + str(t.sourceline) + "! Please investigate.")
  #       message.configure(fg="red")
  #       return
  #
  #   q.write(IOH_xmlfile)
  #   entry.delete(0, END)
  #   entry.insert(0, IOH_xmlfile)
  #
  #   statusText.set("Speaker reformatting for transcript `{}' is complete.".format(IOH_xmlfile))
  #   message.configure(fg="dark green")



# Pretty-print the XML   @TODO Broken.  No longer worth the effort?

# def do_pretty(filename):
#   flash("Now inside the do_pretty function.", 'info')
#
#   filepath = "{0}/{1}".format(app.config['UPLOAD_FOLDER'], filename)
#   flash("Attempting to open '{}'.".format(filepath), 'info')
#   result = "Process is incomplete!"
#
#   pretty = make_new_filename(filepath, 'pretty')
#
#   # Make it pretty
#
#   try:
#     with open(filepath, 'r') as xmlfile, open(pretty, 'w+') as prettyfile:
#       try:
#         bs = BeautifulSoup(xmlfile)
#         prettyfile.write(bs.prettify( ))
#         flash(bs.prettify( ), 'info')
#       except:
#         msg = "Unexpected error: {}".format(sys.exc_info()[0])
#         flash(msg, 'error')
#         return redirect(url_for('main'))
#
#     flash("XML pretty-print has been applied in '{}'.".format(pretty), 'info')
#
#     result = "Pretty-printing is complete. File '{0}' was processed to create '{1}'.".format(filename, pretty)
#
#   except:
#     msg = "Unexpected error: {}".format(sys.exc_info()[0])
#     flash(msg, 'error')
#     return redirect(url_for('main'))
#
#   return result
