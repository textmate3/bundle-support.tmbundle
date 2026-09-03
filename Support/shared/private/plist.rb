$LOAD_PATH << "#{ENV['TM_SUPPORT_PATH']}/private/vendor/CFPropertyList/lib"

# Steer CFPropertyList past libxml-ruby (hangs on Ruby 4.0 / libxml-ruby 2.9.0).
# CFPropertyList's auto-detect order is libxml-ruby → nokogiri → REXML; poisoning
# $LOADED_FEATURES makes the inner `require 'libxml'` return false silently, then
# the LibXML:: constant references NameError out and the outer rescue moves on.
require 'rubygems'
$LOADED_FEATURES.concat(Gem.find_files('libxml.rb'))
$LOADED_FEATURES.concat(Gem.find_files('libxml/libxml.rb'))

require 'cfpropertylist'
require 'shellwords'

module Plist
  module_function

  def load(input)
    raw = read_input(input)
    # No data is a valid answer: the dialog tool writes nothing when a menu or
    # window is dismissed, and callers test for nil.
    return nil if raw.nil? || raw.strip.empty?
    CFPropertyList.native_types(CFPropertyList::List.new(data: raw).value)
  rescue CFFormatError
    # Strict XML parsers (nokogiri, REXML) reject TextMate bundle files that
    # embed raw control bytes (e.g. ESC 0x1B inside <string>~\x1B</string> for
    # Esc-keyed keyEquivalents). plutil tolerates them; round-trip through
    # binary plist to bypass XML strictness while preserving every byte.
    path = write_temp_for_plutil(raw, input)
    begin
      binary = IO.popen(['plutil', '-convert', 'binary1', '-o', '-', path], 'rb', &:read)
      raise unless $?.success?
      CFPropertyList.native_types(CFPropertyList::List.new(data: binary).value)
    ensure
      File.unlink(path) if path && File.exist?(path)
    end
  end

  def dump(obj, format: :xml)
    cf_format = { xml: CFPropertyList::List::FORMAT_XML,
                  binary: CFPropertyList::List::FORMAT_BINARY,
                  plain: CFPropertyList::List::FORMAT_PLAIN }.fetch(format)
    plist = CFPropertyList::List.new
    plist.value = CFPropertyList.guess(obj)
    plist.to_str(cf_format)
  end

  def read_input(input)
    return input.read              if input.respond_to?(:read)
    return File.binread(input)     if input.is_a?(String) && !input.include?("\0") && File.exist?(input)
    input
  end

  def write_temp_for_plutil(raw, original)
    return original if original.is_a?(String) && !original.include?("\0") && File.exist?(original)
    require 'tempfile'
    f = Tempfile.new(['plist-fallback', '.plist'])
    f.binmode
    f.write(raw)
    f.close
    f.path
  end

  class << self
    private :read_input, :write_temp_for_plutil
  end
end

# CFPropertyList already monkey-patches Array#to_plist / Hash#to_plist /
# Enumerator#to_plist to default to FORMAT_BINARY. We want XML by default (to
# match tm_dialog IPC expectations). Use Module#prepend so the existing methods
# are overlaid without firing -w "method redefined" warnings.
module PlistXmlDefault
  def to_plist(options = {})
    options[:plist_format] ||= CFPropertyList::List::FORMAT_XML
    super
  end
end

[Array, Enumerator, Hash].each { |cls| cls.prepend(PlistXmlDefault) }
